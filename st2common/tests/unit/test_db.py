# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import jsonschema

import mock
import mongoengine.connection
from oslo_config import cfg
from pymongo.errors import ConnectionFailure

from st2common.constants.triggers import TRIGGER_INSTANCE_PROCESSED
from st2common.models.system.common import ResourceReference
from st2common.transport.publishers import PoolPublisher
from st2common.util import schema as util_schema
from st2common.util import reference
from st2common.models.db import db_setup
from st2common.util import date as date_utils
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.trigger import TriggerTypeDB, TriggerDB, TriggerInstanceDB
from st2common.models.db.rule import RuleDB, ActionExecutionSpecDB
from st2common.persistence.cleanup import db_cleanup
from st2common.persistence.rule import Rule
from st2common.persistence.trigger import TriggerType, Trigger, TriggerInstance
from st2tests import DbTestCase

SKIP_DELETE = False
DUMMY_DESCRIPTION = 'Sample Description.'


class DbConnectionTest(DbTestCase):

    def test_check_connect(self):
        """
        Tests connectivity to the db server. Requires the db server to be
        running.
        """
        client = mongoengine.connection.get_connection()

        expected_str = "host=['%s:%s']" % (cfg.CONF.database.host, cfg.CONF.database.port)
        self.assertTrue(expected_str in str(client), 'Not connected to desired host.')

    @mock.patch('st2common.models.db.mongoengine')
    @mock.patch('st2common.models.db.LOG')
    def test_db_setup_connecting_info_logging(self, mock_log, mock_mongoengine):
        # Verify that password is not included in the log message
        db_name = 'st2'
        db_port = '27017'
        username = 'user_st2'
        password = 'pass_st2'

        # 1. Password provided as separate argument
        db_host = 'localhost'
        username = 'user_st2'
        password = 'pass_st2'
        db_setup(db_name=db_name, db_host=db_host, db_port=db_port, username=username,
                 password=password)

        expected_message = 'Connecting to database "st2" @ "localhost:27017" as user "user_st2".'
        actual_message = mock_log.info.call_args_list[0][0][0]
        self.assertEqual(expected_message, actual_message)

        # Check for helpful error messages if the connection is successful
        expected_log_message = ('Successfully connected to database "st2" @ "localhost:27017" as '
                                'user "user_st2".')
        actual_log_message = mock_log.info.call_args_list[1][0][0]
        self.assertEqual(expected_log_message, actual_log_message)

        # 2. Password provided as part of uri string (single host)
        db_host = 'mongodb://user_st22:pass_st22@127.0.0.2:5555'
        username = None
        password = None
        db_setup(db_name=db_name, db_host=db_host, db_port=db_port, username=username,
                 password=password)

        expected_message = 'Connecting to database "st2" @ "127.0.0.2:5555" as user "user_st22".'
        actual_message = mock_log.info.call_args_list[2][0][0]
        self.assertEqual(expected_message, actual_message)

        expected_log_message = ('Successfully connected to database "st2" @ "127.0.0.2:5555" as '
                                'user "user_st22".')
        actual_log_message = mock_log.info.call_args_list[3][0][0]
        self.assertEqual(expected_log_message, actual_log_message)

        # 3. Password provided as part of uri string (single host) - username
        # provided as argument has precedence
        db_host = 'mongodb://user_st210:pass_st23@127.0.0.2:5555'
        username = 'user_st23'
        password = None
        db_setup(db_name=db_name, db_host=db_host, db_port=db_port, username=username,
                 password=password)

        expected_message = 'Connecting to database "st2" @ "127.0.0.2:5555" as user "user_st23".'
        actual_message = mock_log.info.call_args_list[4][0][0]
        self.assertEqual(expected_message, actual_message)

        expected_log_message = ('Successfully connected to database "st2" @ "127.0.0.2:5555" as '
                                'user "user_st23".')
        actual_log_message = mock_log.info.call_args_list[5][0][0]
        self.assertEqual(expected_log_message, actual_log_message)

        # 4. Just host provided in the url string
        db_host = 'mongodb://127.0.0.2:5555'
        username = 'user_st24'
        password = 'foobar'
        db_setup(db_name=db_name, db_host=db_host, db_port=db_port, username=username,
                 password=password)

        expected_message = 'Connecting to database "st2" @ "127.0.0.2:5555" as user "user_st24".'
        actual_message = mock_log.info.call_args_list[6][0][0]
        self.assertEqual(expected_message, actual_message)

        expected_log_message = ('Successfully connected to database "st2" @ "127.0.0.2:5555" as '
                                'user "user_st24".')
        actual_log_message = mock_log.info.call_args_list[7][0][0]
        self.assertEqual(expected_log_message, actual_log_message)

        # 5. Multiple hosts specified as part of connection uri
        db_host = 'mongodb://user6:pass6@host1,host2,host3'
        username = None
        password = 'foobar'
        db_setup(db_name=db_name, db_host=db_host, db_port=db_port, username=username,
                 password=password)

        expected_message = ('Connecting to database "st2" @ "host1:27017,host2:27017,host3:27017 '
                            '(replica set)" as user "user6".')
        actual_message = mock_log.info.call_args_list[8][0][0]
        self.assertEqual(expected_message, actual_message)

        expected_log_message = ('Successfully connected to database "st2" @ '
                                '"host1:27017,host2:27017,host3:27017 '
                                '(replica set)" as user "user6".')
        actual_log_message = mock_log.info.call_args_list[9][0][0]
        self.assertEqual(expected_log_message, actual_log_message)

        # 6. Check for error message when failing to establish a connection
        mock_connect = mock.Mock()
        mock_connect.admin.command = mock.Mock(side_effect=ConnectionFailure('Failed to connect'))
        mock_mongoengine.connection.connect.return_value = mock_connect

        db_host = 'mongodb://localhost:9797'
        username = 'user_st2'
        password = 'pass_st2'

        expected_msg = 'Failed to connect'
        self.assertRaisesRegexp(ConnectionFailure, expected_msg, db_setup,
                                db_name=db_name, db_host=db_host, db_port=db_port,
                                username=username, password=password)

        expected_message = 'Connecting to database "st2" @ "localhost:9797" as user "user_st2".'
        actual_message = mock_log.info.call_args_list[10][0][0]
        self.assertEqual(expected_message, actual_message)

        expected_message = ('Failed to connect to database "st2" @ "localhost:9797" as user '
                            '"user_st2": Failed to connect')
        actual_message = mock_log.error.call_args_list[0][0][0]
        self.assertEqual(expected_message, actual_message)


class DbCleanupTest(DbTestCase):
    ensure_indexes = True

    def test_cleanup(self):
        """
        Tests dropping the database. Requires the db server to be running.
        """
        self.assertIn(cfg.CONF.database.db_name, self.db_connection.database_names())

        connection = db_cleanup()

        self.assertNotIn(cfg.CONF.database.db_name, connection.database_names())


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ReactorModelTest(DbTestCase):

    def test_triggertype_crud(self):
        saved = ReactorModelTest._create_save_triggertype()
        retrieved = TriggerType.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same triggertype was not returned.')
        # test update
        self.assertEqual(retrieved.description, '')
        retrieved.description = DUMMY_DESCRIPTION
        saved = TriggerType.add_or_update(retrieved)
        retrieved = TriggerType.get_by_id(saved.id)
        self.assertEqual(retrieved.description, DUMMY_DESCRIPTION, 'Update to trigger failed.')
        # cleanup
        ReactorModelTest._delete([retrieved])
        try:
            retrieved = TriggerType.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_trigger_crud(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        saved = ReactorModelTest._create_save_trigger(triggertype)
        retrieved = Trigger.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same trigger was not returned.')
        # test update
        self.assertEqual(retrieved.description, '')
        retrieved.description = DUMMY_DESCRIPTION
        saved = Trigger.add_or_update(retrieved)
        retrieved = Trigger.get_by_id(saved.id)
        self.assertEqual(retrieved.description, DUMMY_DESCRIPTION, 'Update to trigger failed.')
        # cleanup
        ReactorModelTest._delete([retrieved, triggertype])
        try:
            retrieved = Trigger.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_triggerinstance_crud(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        trigger = ReactorModelTest._create_save_trigger(triggertype)
        saved = ReactorModelTest._create_save_triggerinstance(trigger)
        retrieved = TriggerInstance.get_by_id(saved.id)
        self.assertIsNotNone(retrieved, 'No triggerinstance created.')
        ReactorModelTest._delete([retrieved, trigger, triggertype])
        try:
            retrieved = TriggerInstance.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_rule_crud(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        trigger = ReactorModelTest._create_save_trigger(triggertype)
        runnertype = ActionModelTest._create_save_runnertype()
        action = ActionModelTest._create_save_action(runnertype)
        saved = ReactorModelTest._create_save_rule(trigger, action)
        retrieved = Rule.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name, 'Same rule was not returned.')
        # test update
        self.assertEqual(retrieved.enabled, True)
        retrieved.enabled = False
        saved = Rule.add_or_update(retrieved)
        retrieved = Rule.get_by_id(saved.id)
        self.assertEqual(retrieved.enabled, False, 'Update to rule failed.')
        # cleanup
        ReactorModelTest._delete([retrieved, trigger, action, runnertype, triggertype])
        try:
            retrieved = Rule.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_rule_lookup(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        trigger = ReactorModelTest._create_save_trigger(triggertype)
        runnertype = ActionModelTest._create_save_runnertype()
        action = ActionModelTest._create_save_action(runnertype)
        saved = ReactorModelTest._create_save_rule(trigger, action)
        retrievedrules = Rule.query(trigger=reference.get_str_resource_ref_from_model(trigger))
        self.assertEqual(1, len(retrievedrules), 'No rules found.')
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id, 'Incorrect rule returned.')
        ReactorModelTest._delete([saved, trigger, action, runnertype, triggertype])

    def test_rule_lookup_enabled(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        trigger = ReactorModelTest._create_save_trigger(triggertype)
        runnertype = ActionModelTest._create_save_runnertype()
        action = ActionModelTest._create_save_action(runnertype)
        saved = ReactorModelTest._create_save_rule(trigger, action)
        retrievedrules = Rule.query(trigger=reference.get_str_resource_ref_from_model(trigger),
                                    enabled=True)
        self.assertEqual(1, len(retrievedrules), 'Error looking up enabled rules.')
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id,
                             'Incorrect rule returned.')
        ReactorModelTest._delete([saved, trigger, action, runnertype, triggertype])

    def test_rule_lookup_disabled(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        trigger = ReactorModelTest._create_save_trigger(triggertype)
        runnertype = ActionModelTest._create_save_runnertype()
        action = ActionModelTest._create_save_action(runnertype)
        saved = ReactorModelTest._create_save_rule(trigger, action, False)
        retrievedrules = Rule.query(trigger=reference.get_str_resource_ref_from_model(trigger),
                                    enabled=False)
        self.assertEqual(1, len(retrievedrules), 'Error looking up enabled rules.')
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id, 'Incorrect rule returned.')
        ReactorModelTest._delete([saved, trigger, action, runnertype, triggertype])

    def test_trigger_lookup(self):
        triggertype = ReactorModelTest._create_save_triggertype()
        saved = ReactorModelTest._create_save_trigger(triggertype)
        retrievedtriggers = Trigger.query(name=saved.name)
        self.assertEqual(1, len(retrievedtriggers), 'No triggers found.')
        for retrievedtrigger in retrievedtriggers:
            self.assertEqual(saved.id, retrievedtrigger.id,
                             'Incorrect trigger returned.')
        ReactorModelTest._delete([saved, triggertype])

    @staticmethod
    def _create_save_triggertype():
        created = TriggerTypeDB(pack='dummy_pack_1', name='triggertype-1', description='',
                                payload_schema={}, parameters_schema={})
        return Trigger.add_or_update(created)

    @staticmethod
    def _create_save_trigger(triggertype):
        created = TriggerDB(pack='dummy_pack_1', name='trigger-1', description='',
                            type=triggertype.get_reference().ref, parameters={})
        return Trigger.add_or_update(created)

    @staticmethod
    def _create_save_triggerinstance(trigger):
        created = TriggerInstanceDB(trigger=trigger.get_reference().ref, payload={},
                                    occurrence_time=date_utils.get_datetime_utc_now(),
                                    status=TRIGGER_INSTANCE_PROCESSED)
        return TriggerInstance.add_or_update(created)

    @staticmethod
    def _create_save_rule(trigger, action=None, enabled=True):
        name = 'rule-1'
        pack = 'default'
        ref = ResourceReference.to_string_reference(name=name, pack=pack)
        created = RuleDB(name=name, pack=pack, ref=ref)
        created.description = ''
        created.enabled = enabled
        created.trigger = reference.get_str_resource_ref_from_model(trigger)
        created.criteria = {}
        created.action = ActionExecutionSpecDB()
        action_ref = ResourceReference(pack=action.pack, name=action.name).ref
        created.action.ref = action_ref
        created.action.pack = action.pack
        created.action.parameters = {}
        return Rule.add_or_update(created)

    @staticmethod
    def _delete(model_objects):
        global SKIP_DELETE
        if SKIP_DELETE:
            return
        for model_object in model_objects:
            model_object.delete()


from st2common.models.db.action import ActionDB
from st2common.models.db.runner import RunnerTypeDB
from st2common.models.db.notification import NotificationSchema, NotificationSubSchema
from st2common.persistence.action import Action
from st2common.persistence.runner import RunnerType


PARAM_SCHEMA = {
    "title": "action-1",
    "description": "awesomeness",
    "type": "object",
    "properties": {
        "r1": {
            "type": "object",
            "properties": {
                "r1a": {
                    "type": "string"
                }
            }
        },
        "r2": {
            "type": "string",
            "required": True
        },
        "p1": {
            "type": "string",
            "required": True
        },
        "p2": {
            "type": "number",
            "default": 2868
        },
        "p3": {
            "type": "boolean",
            "default": False
        }
    },
    "additionalProperties": False
}


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ActionModelTest(DbTestCase):

    def tearDown(self):
        runnertype = RunnerType.get_by_name('python')
        self._delete([runnertype])
        super(ActionModelTest, self).tearDown()

    def test_action_crud(self):
        runnertype = self._create_save_runnertype(metadata=False)
        saved = self._create_save_action(runnertype, metadata=False)
        retrieved = Action.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name,
                         'Same Action was not returned.')

        # test update
        self.assertEqual(retrieved.description, 'awesomeness')
        retrieved.description = DUMMY_DESCRIPTION
        saved = Action.add_or_update(retrieved)
        retrieved = Action.get_by_id(saved.id)
        self.assertEqual(retrieved.description, DUMMY_DESCRIPTION, 'Update to action failed.')

        # cleanup
        self._delete([retrieved])
        try:
            retrieved = Action.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_action_with_notify_crud(self):
        runnertype = self._create_save_runnertype(metadata=False)
        saved = self._create_save_action(runnertype, metadata=False)

        # Update action with notification settings
        on_complete = NotificationSubSchema(message='Action complete.')
        saved.notify = NotificationSchema(on_complete=on_complete)
        saved = Action.add_or_update(saved)

        # Check if notification settings were set correctly.
        retrieved = Action.get_by_id(saved.id)
        self.assertEqual(retrieved.notify.on_complete.message, on_complete.message)

        # Now reset notify in action to empty and validate it's gone.
        retrieved.notify = NotificationSchema(on_complete=None)
        saved = Action.add_or_update(retrieved)
        retrieved = Action.get_by_id(saved.id)
        self.assertEqual(retrieved.notify.on_complete, None)

        # cleanup
        self._delete([retrieved])
        try:
            retrieved = Action.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_parameter_schema(self):
        runnertype = self._create_save_runnertype(metadata=True)
        saved = self._create_save_action(runnertype, metadata=True)
        retrieved = Action.get_by_id(saved.id)

        # validate generated schema
        schema = util_schema.get_schema_for_action_parameters(retrieved)
        self.assertDictEqual(schema, PARAM_SCHEMA)
        validator = util_schema.get_validator()
        validator.check_schema(schema)

        # use schema to validate parameters
        jsonschema.validate({"r2": "abc", "p1": "def"}, schema, validator)
        jsonschema.validate({"r2": "abc", "p1": "def", "r1": {"r1a": "ghi"}}, schema, validator)
        self.assertRaises(jsonschema.ValidationError, jsonschema.validate,
                          '{"r2": "abc", "p1": "def"}', schema, validator)
        self.assertRaises(jsonschema.ValidationError, jsonschema.validate,
                          {"r2": "abc"}, schema, validator)
        self.assertRaises(jsonschema.ValidationError, jsonschema.validate,
                          {"r2": "abc", "p1": "def", "r1": 123}, schema, validator)

        # cleanup
        self._delete([retrieved])
        try:
            retrieved = Action.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_parameters_schema_runner_and_action_parameters_are_correctly_merged(self):
        # Test that the runner and action parameters are correctly deep merged when building
        # action parameters schema

        self._create_save_runnertype(metadata=True)

        action_db = mock.Mock()
        action_db.runner_type = {'name': 'python'}
        action_db.parameters = {'r1': {'immutable': True}}

        schema = util_schema.get_schema_for_action_parameters(action_db=action_db)
        expected = {
            u'type': u'object',
            u'properties': {
                u'r1a': {
                    u'type': u'string'
                }
            },
            'immutable': True
        }
        self.assertEqual(schema['properties']['r1'], expected)

    @staticmethod
    def _create_save_runnertype(metadata=False):
        created = RunnerTypeDB(name='python')
        created.description = ''
        created.enabled = True
        if not metadata:
            created.runner_parameters = {'r1': None, 'r2': None}
        else:
            created.runner_parameters = {
                'r1': {'type': 'object', 'properties': {'r1a': {'type': 'string'}}},
                'r2': {'type': 'string', 'required': True}
            }
        created.runner_module = 'nomodule'
        return RunnerType.add_or_update(created)

    @staticmethod
    def _create_save_action(runnertype, metadata=False):
        name = 'action-1'
        pack = 'wolfpack'
        ref = ResourceReference(pack=pack, name=name).ref
        created = ActionDB(name=name, description='awesomeness', enabled=True,
                           entry_point='/tmp/action.py', pack=pack,
                           ref=ref,
                           runner_type={'name': runnertype.name})

        if not metadata:
            created.parameters = {'p1': None, 'p2': None, 'p3': None}
        else:
            created.parameters = {
                'p1': {'type': 'string', 'required': True},
                'p2': {'type': 'number', 'default': 2868},
                'p3': {'type': 'boolean', 'default': False}
            }
        return Action.add_or_update(created)

    @staticmethod
    def _delete(model_objects):
        global SKIP_DELETE
        if SKIP_DELETE:
            return
        for model_object in model_objects:
            model_object.delete()


from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair


class KeyValuePairModelTest(DbTestCase):

    def test_kvp_crud(self):
        saved = KeyValuePairModelTest._create_save_kvp()
        retrieved = KeyValuePair.get_by_name(saved.name)
        self.assertEqual(saved.id, retrieved.id,
                         'Same KeyValuePair was not returned.')

        # test update
        self.assertEqual(retrieved.value, '0123456789ABCDEF')
        retrieved.value = 'ABCDEF0123456789'
        saved = KeyValuePair.add_or_update(retrieved)
        retrieved = KeyValuePair.get_by_name(saved.name)
        self.assertEqual(retrieved.value, 'ABCDEF0123456789',
                         'Update of key value failed')

        # cleanup
        KeyValuePairModelTest._delete([retrieved])
        try:
            retrieved = KeyValuePair.get_by_name(saved.name)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    @staticmethod
    def _create_save_kvp():
        created = KeyValuePairDB(name='token', value='0123456789ABCDEF')
        return KeyValuePair.add_or_update(created)

    @staticmethod
    def _delete(model_objects):
        global SKIP_DELETE
        if SKIP_DELETE:
            return
        for model_object in model_objects:
            model_object.delete()
