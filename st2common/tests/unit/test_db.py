# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

# NOTE: We need to perform monkeypatch before importing ssl module otherwise tests will fail.
# See https://github.com/StackStorm/st2/pull/4834 for details
from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import time

import jsonschema
import mock
import mongoengine.connection
from mongoengine.connection import disconnect
from oslo_config import cfg
from pymongo.errors import ConnectionFailure
from pymongo.errors import ServerSelectionTimeoutError

from st2common.constants.triggers import TRIGGER_INSTANCE_PROCESSED
from st2common.models.system.common import ResourceReference
from st2common.transport.publishers import PoolPublisher
from st2common.util import schema as util_schema
from st2common.util import reference
from st2common.models.db import db_setup
from st2common.models.db import _get_tls_kwargs
from st2common.util import date as date_utils
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.trigger import TriggerTypeDB, TriggerDB, TriggerInstanceDB
from st2common.models.db.rule import RuleDB, ActionExecutionSpecDB
from st2common.persistence.cleanup import db_cleanup
from st2common.persistence.rule import Rule
from st2common.persistence.trigger import TriggerType, Trigger, TriggerInstance
from st2tests import DbTestCase

from unittest import TestCase
from st2tests.base import ALL_MODELS


__all__ = [
    "DbConnectionTestCase",
    "DbConnectionTestCase",
    "ReactorModelTestCase",
    "ActionModelTestCase",
    "KeyValuePairModelTestCase",
]

SKIP_DELETE = False
DUMMY_DESCRIPTION = "Sample Description."


class DbIndexNameTestCase(TestCase):
    """
    Test which verifies that model index name are not longer than the specified limit.
    """

    LIMIT = 65

    def test_index_name_length(self):
        db_name = "st2"

        for model in ALL_MODELS:
            collection_name = model._get_collection_name()
            model_indexes = model._meta["index_specs"]

            for index_specs in model_indexes:
                index_name = index_specs.get("name", None)
                if index_name:
                    # Custom index name defined by the developer
                    index_field_name = index_name
                else:
                    # No explicit index name specified, one is auto-generated using
                    # <db name>.<collection name>.<index field names> schema
                    index_fields = dict(index_specs["fields"]).keys()
                    index_field_name = ".".join(index_fields)

                index_name = "%s.%s.%s" % (db_name, collection_name, index_field_name)

                if len(index_name) > self.LIMIT:
                    self.fail(
                        'Index name "%s" for model "%s" is longer than %s characters. '
                        "Please manually define name for this index so it's shorter than "
                        "that" % (index_name, model.__name__, self.LIMIT)
                    )


class DbConnectionTestCase(DbTestCase):
    def setUp(self):
        # NOTE: It's important we re-establish a connection on each setUp
        self.setUpClass()
        cfg.CONF.reset()

    def tearDown(self):
        # NOTE: It's important we disconnect here otherwise tests will fail
        disconnect()
        cfg.CONF.reset()

    @classmethod
    def tearDownClass(cls):
        # since tearDown discconnects, dropping the database in tearDownClass
        # fails without establishing a new connection.
        cls._establish_connection_and_re_create_db()
        super().tearDownClass()

    def test_check_connect(self):
        """
        Tests connectivity to the db server. Requires the db server to be
        running.
        """
        client = mongoengine.connection.get_connection()

        expected_str = "host=['%s:%s']" % (
            cfg.CONF.database.host,
            cfg.CONF.database.port,
        )
        self.assertIn(expected_str, str(client), "Not connected to desired host.")

    def test_network_level_compression(self):
        disconnect()

        # db is not modified in this test, so this is safe to run in parallel.
        db_name = "st2"
        db_host = "localhost"
        db_port = 27017

        # If running version < MongoDB 4.2 we skip this check since zstd is only supported in server
        # >= 4.2
        connection = db_setup(
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            ensure_indexes=False,
        )
        server_version = tuple(
            [int(x) for x in connection.server_info()["version"].split(".")]
        )

        if server_version < (4, 2, 0):
            self.skipTest("Skipping test since running MongoDB < 4.2")
            return

        disconnect()

        # 1. Verify default is no compression
        connection = db_setup(
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            ensure_indexes=False,
        )
        # Sadly there is no nicer way to assert that it seems
        self.assertFalse("compressors=['zstd']" in str(connection))
        self.assertFalse("compressors" in str(connection))

        # 2. Verify using zstd works - specified using config option
        disconnect()

        cfg.CONF.set_override(name="compressors", group="database", override="zstd")

        connection = db_setup(
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            ensure_indexes=False,
        )
        # Sadly there is no nicer way to assert that it seems
        self.assertTrue("compressors=['zstd']" in str(connection))

        # 3. Verify using zstd works - specified inside URI
        disconnect()

        cfg.CONF.set_override(name="compressors", group="database", override=None)
        db_host = "mongodb://127.0.0.1/?compressors=zstd"

        connection = db_setup(
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            ensure_indexes=False,
        )
        # Sadly there is no nicer way to assert that it seems
        self.assertTrue("compressors=['zstd']" in str(connection))

        # 4. Verify using zlib works - specified using config option
        disconnect()

        cfg.CONF.set_override(name="compressors", group="database", override="zlib")
        cfg.CONF.set_override(
            name="zlib_compression_level", group="database", override=8
        )

        connection = db_setup(
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            ensure_indexes=False,
        )
        # Sadly there is no nicer way to assert that it seems
        self.assertTrue("compressors=['zlib']" in str(connection))
        self.assertTrue("zlibcompressionlevel=8" in str(connection))

        # 5. Verify using zlib works - specified inside URI
        disconnect()

        cfg.CONF.set_override(name="compressors", group="database", override=None)
        cfg.CONF.set_override(
            name="zlib_compression_level", group="database", override=None
        )
        db_host = "mongodb://127.0.0.1/?compressors=zlib&zlibCompressionLevel=9"

        connection = db_setup(
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            ensure_indexes=False,
        )
        # Sadly there is no nicer way to assert that it seems
        self.assertTrue("compressors=['zlib']" in str(connection))
        self.assertTrue("zlibcompressionlevel=9" in str(connection))

    def test_get_tls_kwargs(self):
        # 1. No SSL kwargs provided
        tls_kwargs = _get_tls_kwargs()
        self.assertEqual(tls_kwargs, {"tls": False})

        # 2. tls kwarg provided
        tls_kwargs = _get_tls_kwargs(tls=True)
        self.assertEqual(tls_kwargs, {"tls": True, "tlsAllowInvalidHostnames": False})

        # 3. authentication_mechanism kwarg provided
        tls_kwargs = _get_tls_kwargs(authentication_mechanism="MONGODB-X509")
        self.assertEqual(
            tls_kwargs,
            {
                "tls": True,
                "tlsAllowInvalidHostnames": False,
                "authentication_mechanism": "MONGODB-X509",
            },
        )

        # 4a. tls_certificate_key_file provided
        tls_kwargs = _get_tls_kwargs(tls_certificate_key_file="/tmp/keyfile")
        self.assertEqual(
            tls_kwargs,
            {
                "tls": True,
                "tlsCertificateKeyFile": "/tmp/keyfile",
                "tlsAllowInvalidHostnames": False,
            },
        )

        # 4b. tls_certificate_key_file_password provided with tls_certificate_key_file
        tls_kwargs = _get_tls_kwargs(
            tls_certificate_key_file="/tmp/keyfile",
            tls_certificate_key_file_password="pass",
        )
        self.assertEqual(
            tls_kwargs,
            {
                "tls": True,
                "tlsCertificateKeyFile": "/tmp/keyfile",
                "tlsCertificateKeyFilePassword": "pass",
                "tlsAllowInvalidHostnames": False,
            },
        )

        # 4c. tls_certificate_key_file_password provided without tls_certificate_key_file
        tls_kwargs = _get_tls_kwargs(tls_certificate_key_file_password="pass")
        self.assertEqual(tls_kwargs, {"tls": False})

        # 5. tls_ca_file provided
        tls_kwargs = _get_tls_kwargs(tls_ca_file="/tmp/ca_certs")
        self.assertEqual(
            tls_kwargs,
            {
                "tls": True,
                "tlsCAFile": "/tmp/ca_certs",
                "tlsAllowInvalidHostnames": False,
            },
        )

        # 6. tls_ca_file and ssl_cert_reqs combinations
        tls_kwargs = _get_tls_kwargs(tls_ca_file="/tmp/ca_certs", ssl_cert_reqs="none")
        self.assertEqual(
            tls_kwargs,
            {
                "tls": True,
                "tlsCAFile": "/tmp/ca_certs",
                "tlsAllowInvalidCertificates": True,
                "tlsAllowInvalidHostnames": False,
            },
        )

        tls_kwargs = _get_tls_kwargs(
            tls_ca_file="/tmp/ca_certs", ssl_cert_reqs="optional"
        )
        self.assertEqual(
            tls_kwargs,
            {
                "tls": True,
                "tlsCAFile": "/tmp/ca_certs",
                "tlsAllowInvalidCertificates": False,
                "tlsAllowInvalidHostnames": False,
            },
        )

        tls_kwargs = _get_tls_kwargs(
            tls_ca_file="/tmp/ca_certs", ssl_cert_reqs="required"
        )
        self.assertEqual(
            tls_kwargs,
            {
                "tls": True,
                "tlsCAFile": "/tmp/ca_certs",
                "tlsAllowInvalidCertificates": False,
                "tlsAllowInvalidHostnames": False,
            },
        )

        # 7. tls_allow_invalid_certificates provided (does not implicitly enable tls)
        for allow_invalid in (True, False):
            tls_kwargs = _get_tls_kwargs(tls_allow_invalid_certificates=allow_invalid)
            self.assertEqual(
                tls_kwargs,
                {
                    "tls": False,
                    "tlsAllowInvalidCertificates": allow_invalid,
                },
            )

            # make sure ssl_cert_reqs is ignored if tls_allow_invalid_certificates is set
            for ssl_cert_reqs in ("none", "optional", "required"):
                tls_kwargs = _get_tls_kwargs(
                    ssl_cert_reqs=ssl_cert_reqs,
                    tls_allow_invalid_certificates=allow_invalid,
                )
                self.assertEqual(
                    tls_kwargs,
                    {
                        "tls": False,
                        "tlsAllowInvalidCertificates": allow_invalid,
                    },
                )

    @mock.patch("st2common.models.db.mongoengine")
    def test_db_setup(self, mock_mongoengine):
        db_setup(
            db_name="name",
            db_host="host",
            db_port=12345,
            username="username",
            password="password",
            authentication_mechanism="MONGODB-X509",
            ensure_indexes=False,
        )

        call_args = mock_mongoengine.connection.connect.call_args_list[0][0]
        call_kwargs = mock_mongoengine.connection.connect.call_args_list[0][1]

        self.assertEqual(call_args, ("name",))
        self.assertEqual(
            call_kwargs,
            {
                "host": "host",
                "port": 12345,
                "username": "username",
                "password": "password",
                "tz_aware": True,
                "authentication_mechanism": "MONGODB-X509",
                "tls": True,
                "tlsAllowInvalidHostnames": False,
                "connectTimeoutMS": 3000,
                "serverSelectionTimeoutMS": 3000,
                "uuidRepresentation": "pythonLegacy",
            },
        )

    @mock.patch("st2common.models.db.mongoengine")
    @mock.patch("st2common.models.db.LOG")
    def test_db_setup_connecting_info_logging(self, mock_log, mock_mongoengine):
        # Verify that password is not included in the log message
        db_name = "st2"
        db_port = "27017"
        username = "user_st2"
        password = "pass_st2"

        # 1. Password provided as separate argument
        db_host = "localhost"
        username = "user_st2"
        password = "pass_st2"
        db_setup(
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            username=username,
            password=password,
            ensure_indexes=False,
        )

        expected_message = (
            'Connecting to database "st2" @ "localhost:27017" as user "user_st2".'
        )
        actual_message = mock_log.info.call_args_list[0][0][0]
        self.assertEqual(expected_message, actual_message)

        # Check for helpful error messages if the connection is successful
        expected_log_message = (
            'Successfully connected to database "st2" @ "localhost:27017" as '
            'user "user_st2".'
        )
        actual_log_message = mock_log.info.call_args_list[1][0][0]
        self.assertEqual(expected_log_message, actual_log_message)

        # 2. Password provided as part of uri string (single host)
        db_host = "mongodb://user_st22:pass_st22@127.0.0.2:5555"
        username = None
        password = None
        db_setup(
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            username=username,
            password=password,
            ensure_indexes=False,
        )

        expected_message = (
            'Connecting to database "st2" @ "127.0.0.2:5555" as user "user_st22".'
        )
        actual_message = mock_log.info.call_args_list[2][0][0]
        self.assertEqual(expected_message, actual_message)

        expected_log_message = (
            'Successfully connected to database "st2" @ "127.0.0.2:5555" as '
            'user "user_st22".'
        )
        actual_log_message = mock_log.info.call_args_list[3][0][0]
        self.assertEqual(expected_log_message, actual_log_message)

        # 3. Password provided as part of uri string (single host) - username
        # provided as argument has precedence
        db_host = "mongodb://user_st210:pass_st23@127.0.0.2:5555"
        username = "user_st23"
        password = None
        db_setup(
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            username=username,
            password=password,
            ensure_indexes=False,
        )

        expected_message = (
            'Connecting to database "st2" @ "127.0.0.2:5555" as user "user_st23".'
        )
        actual_message = mock_log.info.call_args_list[4][0][0]
        self.assertEqual(expected_message, actual_message)

        expected_log_message = (
            'Successfully connected to database "st2" @ "127.0.0.2:5555" as '
            'user "user_st23".'
        )
        actual_log_message = mock_log.info.call_args_list[5][0][0]
        self.assertEqual(expected_log_message, actual_log_message)

        # 4. Just host provided in the url string
        db_host = "mongodb://127.0.0.2:5555"
        username = "user_st24"
        password = "foobar"
        db_setup(
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            username=username,
            password=password,
            ensure_indexes=False,
        )

        expected_message = (
            'Connecting to database "st2" @ "127.0.0.2:5555" as user "user_st24".'
        )
        actual_message = mock_log.info.call_args_list[6][0][0]
        self.assertEqual(expected_message, actual_message)

        expected_log_message = (
            'Successfully connected to database "st2" @ "127.0.0.2:5555" as '
            'user "user_st24".'
        )
        actual_log_message = mock_log.info.call_args_list[7][0][0]
        self.assertEqual(expected_log_message, actual_log_message)

        # 5. Multiple hosts specified as part of connection uri
        db_host = "mongodb://user6:pass6@host1,host2,host3"
        username = None
        password = "foobar"
        db_setup(
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            username=username,
            password=password,
            ensure_indexes=False,
        )

        expected_message = (
            'Connecting to database "st2" @ "host1:27017,host2:27017,host3:27017 '
            '(replica set)" as user "user6".'
        )
        actual_message = mock_log.info.call_args_list[8][0][0]
        self.assertEqual(expected_message, actual_message)

        expected_log_message = (
            'Successfully connected to database "st2" @ '
            '"host1:27017,host2:27017,host3:27017 '
            '(replica set)" as user "user6".'
        )
        actual_log_message = mock_log.info.call_args_list[9][0][0]
        self.assertEqual(expected_log_message, actual_log_message)

        # 6. Check for error message when failing to establish a connection
        mock_connect = mock.Mock()
        mock_connect.admin.command = mock.Mock(
            side_effect=ConnectionFailure("Failed to connect")
        )
        mock_mongoengine.connection.connect.return_value = mock_connect

        db_host = "mongodb://localhost:9797"
        username = "user_st2"
        password = "pass_st2"

        expected_msg = "Failed to connect"
        self.assertRaisesRegex(
            ConnectionFailure,
            expected_msg,
            db_setup,
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            username=username,
            password=password,
            ensure_indexes=False,
        )

        expected_message = (
            'Connecting to database "st2" @ "localhost:9797" as user "user_st2".'
        )
        actual_message = mock_log.info.call_args_list[10][0][0]
        self.assertEqual(expected_message, actual_message)

        expected_message = (
            'Failed to connect to database "st2" @ "localhost:9797" as user '
            '"user_st2": Failed to connect'
        )
        actual_message = mock_log.error.call_args_list[0][0][0]
        self.assertEqual(expected_message, actual_message)

    def test_db_connect_server_selection_timeout_ssl_on_non_ssl_listener(self):
        # Verify that the we wait connection_timeout ms (server selection timeout ms) before failing
        # and propagating the error
        disconnect()

        # db is not modified in this test, so this is safe to run in parallel.
        db_name = "st2"
        db_host = "localhost"
        db_port = 27017

        cfg.CONF.set_override(name="connection_timeout", group="database", override=300)

        start = time.time()
        self.assertRaises(
            ServerSelectionTimeoutError,
            db_setup,
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            tls=True,
            ensure_indexes=False,
        )
        end = time.time()
        diff = end - start

        self.assertTrue(diff >= 0.3)

        disconnect()

        cfg.CONF.set_override(name="connection_timeout", group="database", override=200)

        start = time.time()
        self.assertRaises(
            ServerSelectionTimeoutError,
            db_setup,
            db_name=db_name,
            db_host=db_host,
            db_port=db_port,
            tls=True,
            ensure_indexes=False,
        )
        end = time.time()
        diff = end - start

        self.assertTrue(diff >= 0.1)


class DbCleanupTestCase(DbTestCase):
    ensure_indexes = True

    def test_cleanup(self):
        """
        Tests dropping the database. Requires the db server to be running.
        """
        self.assertIn(
            cfg.CONF.database.db_name, self.db_connection.list_database_names()
        )

        connection = db_cleanup()

        self.assertNotIn(cfg.CONF.database.db_name, connection.list_database_names())


@mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
class ReactorModelTestCase(DbTestCase):
    def test_triggertype_crud(self):
        saved = ReactorModelTestCase._create_save_triggertype()
        retrieved = TriggerType.get_by_id(saved.id)
        self.assertEqual(
            saved.name, retrieved.name, "Same triggertype was not returned."
        )
        # test update
        self.assertEqual(retrieved.description, "")
        retrieved.description = DUMMY_DESCRIPTION
        saved = TriggerType.add_or_update(retrieved)
        retrieved = TriggerType.get_by_id(saved.id)
        self.assertEqual(
            retrieved.description, DUMMY_DESCRIPTION, "Update to trigger failed."
        )
        # cleanup
        ReactorModelTestCase._delete([retrieved])
        try:
            retrieved = TriggerType.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, "managed to retrieve after failure.")

    def test_trigger_crud(self):
        triggertype = ReactorModelTestCase._create_save_triggertype()
        saved = ReactorModelTestCase._create_save_trigger(triggertype)
        retrieved = Trigger.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name, "Same trigger was not returned.")
        # test update
        self.assertEqual(retrieved.description, "")
        retrieved.description = DUMMY_DESCRIPTION
        saved = Trigger.add_or_update(retrieved)
        retrieved = Trigger.get_by_id(saved.id)
        self.assertEqual(
            retrieved.description, DUMMY_DESCRIPTION, "Update to trigger failed."
        )
        # cleanup
        ReactorModelTestCase._delete([retrieved, triggertype])
        try:
            retrieved = Trigger.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, "managed to retrieve after failure.")

    def test_triggerinstance_crud(self):
        triggertype = ReactorModelTestCase._create_save_triggertype()
        trigger = ReactorModelTestCase._create_save_trigger(triggertype)
        saved = ReactorModelTestCase._create_save_triggerinstance(trigger)
        retrieved = TriggerInstance.get_by_id(saved.id)
        self.assertIsNotNone(retrieved, "No triggerinstance created.")
        ReactorModelTestCase._delete([retrieved, trigger, triggertype])
        try:
            retrieved = TriggerInstance.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, "managed to retrieve after failure.")

    def test_rule_crud(self):
        triggertype = ReactorModelTestCase._create_save_triggertype()
        trigger = ReactorModelTestCase._create_save_trigger(triggertype)
        runnertype = ActionModelTestCase._create_save_runnertype()
        action = ActionModelTestCase._create_save_action(runnertype)
        saved = ReactorModelTestCase._create_save_rule(trigger, action)
        retrieved = Rule.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name, "Same rule was not returned.")
        # test update
        self.assertEqual(retrieved.enabled, True)
        retrieved.enabled = False
        saved = Rule.add_or_update(retrieved)
        retrieved = Rule.get_by_id(saved.id)
        self.assertEqual(retrieved.enabled, False, "Update to rule failed.")
        # cleanup
        ReactorModelTestCase._delete(
            [retrieved, trigger, action, runnertype, triggertype]
        )
        try:
            retrieved = Rule.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, "managed to retrieve after failure.")

    def test_rule_lookup(self):
        triggertype = ReactorModelTestCase._create_save_triggertype()
        trigger = ReactorModelTestCase._create_save_trigger(triggertype)
        runnertype = ActionModelTestCase._create_save_runnertype()
        action = ActionModelTestCase._create_save_action(runnertype)
        saved = ReactorModelTestCase._create_save_rule(trigger, action)
        retrievedrules = Rule.query(
            trigger=reference.get_str_resource_ref_from_model(trigger)
        )
        self.assertEqual(1, len(retrievedrules), "No rules found.")
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id, "Incorrect rule returned.")
        ReactorModelTestCase._delete([saved, trigger, action, runnertype, triggertype])

    def test_rule_lookup_enabled(self):
        triggertype = ReactorModelTestCase._create_save_triggertype()
        trigger = ReactorModelTestCase._create_save_trigger(triggertype)
        runnertype = ActionModelTestCase._create_save_runnertype()
        action = ActionModelTestCase._create_save_action(runnertype)
        saved = ReactorModelTestCase._create_save_rule(trigger, action)
        retrievedrules = Rule.query(
            trigger=reference.get_str_resource_ref_from_model(trigger), enabled=True
        )
        self.assertEqual(1, len(retrievedrules), "Error looking up enabled rules.")
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id, "Incorrect rule returned.")
        ReactorModelTestCase._delete([saved, trigger, action, runnertype, triggertype])

    def test_rule_lookup_disabled(self):
        triggertype = ReactorModelTestCase._create_save_triggertype()
        trigger = ReactorModelTestCase._create_save_trigger(triggertype)
        runnertype = ActionModelTestCase._create_save_runnertype()
        action = ActionModelTestCase._create_save_action(runnertype)
        saved = ReactorModelTestCase._create_save_rule(trigger, action, False)
        retrievedrules = Rule.query(
            trigger=reference.get_str_resource_ref_from_model(trigger), enabled=False
        )
        self.assertEqual(1, len(retrievedrules), "Error looking up enabled rules.")
        for retrievedrule in retrievedrules:
            self.assertEqual(saved.id, retrievedrule.id, "Incorrect rule returned.")
        ReactorModelTestCase._delete([saved, trigger, action, runnertype, triggertype])

    def test_trigger_lookup(self):
        triggertype = ReactorModelTestCase._create_save_triggertype()
        saved = ReactorModelTestCase._create_save_trigger(triggertype)
        retrievedtriggers = Trigger.query(name=saved.name)
        self.assertEqual(1, len(retrievedtriggers), "No triggers found.")
        for retrievedtrigger in retrievedtriggers:
            self.assertEqual(
                saved.id, retrievedtrigger.id, "Incorrect trigger returned."
            )
        ReactorModelTestCase._delete([saved, triggertype])

    @staticmethod
    def _create_save_triggertype():
        created = TriggerTypeDB(
            pack="dummy_pack_1",
            name="triggertype-1",
            description="",
            payload_schema={},
            parameters_schema={},
        )
        return Trigger.add_or_update(created)

    @staticmethod
    def _create_save_trigger(triggertype):
        created = TriggerDB(
            pack="dummy_pack_1",
            name="trigger-1",
            description="",
            type=triggertype.get_reference().ref,
            parameters={},
        )
        return Trigger.add_or_update(created)

    @staticmethod
    def _create_save_triggerinstance(trigger):
        created = TriggerInstanceDB(
            trigger=trigger.get_reference().ref,
            payload={},
            occurrence_time=date_utils.get_datetime_utc_now(),
            status=TRIGGER_INSTANCE_PROCESSED,
        )
        return TriggerInstance.add_or_update(created)

    @staticmethod
    def _create_save_rule(trigger, action=None, enabled=True):
        name = "rule-1"
        pack = "default"
        ref = ResourceReference.to_string_reference(name=name, pack=pack)
        created = RuleDB(name=name, pack=pack, ref=ref)
        created.description = ""
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
        "r1": {"type": "object", "properties": {"r1a": {"type": "string"}}},
        "r2": {"type": "string", "required": True},
        "p1": {"type": "string", "required": True},
        "p2": {"type": "number", "default": 2868},
        "p3": {"type": "boolean", "default": False},
        "p4": {"type": "string", "secret": True},
    },
    "additionalProperties": False,
}


@mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
class ActionModelTestCase(DbTestCase):
    def tearDown(self):
        runnertype = RunnerType.get_by_name("python")
        self._delete([runnertype])
        super(ActionModelTestCase, self).tearDown()

    def test_action_crud(self):
        runnertype = self._create_save_runnertype(metadata=False)
        saved = self._create_save_action(runnertype, metadata=False)
        retrieved = Action.get_by_id(saved.id)
        self.assertEqual(saved.name, retrieved.name, "Same Action was not returned.")

        # test update
        self.assertEqual(retrieved.description, "awesomeness")
        retrieved.description = DUMMY_DESCRIPTION
        saved = Action.add_or_update(retrieved)
        retrieved = Action.get_by_id(saved.id)
        self.assertEqual(
            retrieved.description, DUMMY_DESCRIPTION, "Update to action failed."
        )

        # cleanup
        self._delete([retrieved])
        try:
            retrieved = Action.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, "managed to retrieve after failure.")

    def test_action_with_notify_crud(self):
        runnertype = self._create_save_runnertype(metadata=False)
        saved = self._create_save_action(runnertype, metadata=False)

        # Update action with notification settings
        on_complete = NotificationSubSchema(message="Action complete.")
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
        self.assertIsNone(retrieved, "managed to retrieve after failure.")

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
        jsonschema.validate(
            {"r2": "abc", "p1": "def", "r1": {"r1a": "ghi"}}, schema, validator
        )
        self.assertRaises(
            jsonschema.ValidationError,
            jsonschema.validate,
            '{"r2": "abc", "p1": "def"}',
            schema,
            validator,
        )
        self.assertRaises(
            jsonschema.ValidationError,
            jsonschema.validate,
            {"r2": "abc"},
            schema,
            validator,
        )
        self.assertRaises(
            jsonschema.ValidationError,
            jsonschema.validate,
            {"r2": "abc", "p1": "def", "r1": 123},
            schema,
            validator,
        )

        # cleanup
        self._delete([retrieved])
        try:
            retrieved = Action.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, "managed to retrieve after failure.")

    def test_parameters_schema_runner_and_action_parameters_are_correctly_merged(self):
        # Test that the runner and action parameters are correctly deep merged when building
        # action parameters schema

        self._create_save_runnertype(metadata=True)

        action_db = mock.Mock()
        action_db.runner_type = {"name": "python"}
        action_db.parameters = {"r1": {"immutable": True}}

        schema = util_schema.get_schema_for_action_parameters(action_db=action_db)
        expected = {
            "type": "object",
            "properties": {"r1a": {"type": "string"}},
            "immutable": True,
        }
        self.assertEqual(schema["properties"]["r1"], expected)

    @staticmethod
    def _create_save_runnertype(metadata=False):
        created = RunnerTypeDB(name="python")
        created.description = ""
        created.enabled = True
        if not metadata:
            created.runner_parameters = {"r1": None, "r2": None}
        else:
            created.runner_parameters = {
                "r1": {"type": "object", "properties": {"r1a": {"type": "string"}}},
                "r2": {"type": "string", "required": True},
            }
        created.runner_module = "nomodule"
        return RunnerType.add_or_update(created)

    @staticmethod
    def _create_save_action(runnertype, metadata=False):
        name = "action-1"
        pack = "wolfpack"
        ref = ResourceReference(pack=pack, name=name).ref
        created = ActionDB(
            name=name,
            description="awesomeness",
            enabled=True,
            entry_point="/tmp/action.py",
            pack=pack,
            ref=ref,
            runner_type={"name": runnertype.name},
        )

        if not metadata:
            created.parameters = {"p1": None, "p2": None, "p3": None, "p4": None}
        else:
            created.parameters = {
                "p1": {"type": "string", "required": True},
                "p2": {"type": "number", "default": 2868},
                "p3": {"type": "boolean", "default": False},
                "p4": {"type": "string", "secret": True},
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


class KeyValuePairModelTestCase(DbTestCase):
    def test_kvp_crud(self):
        saved = KeyValuePairModelTestCase._create_save_kvp()
        retrieved = KeyValuePair.get_by_name(saved.name)
        self.assertEqual(saved.id, retrieved.id, "Same KeyValuePair was not returned.")

        # test update
        self.assertEqual(retrieved.value, "0123456789ABCDEF")
        retrieved.value = "ABCDEF0123456789"
        saved = KeyValuePair.add_or_update(retrieved)
        retrieved = KeyValuePair.get_by_name(saved.name)
        self.assertEqual(
            retrieved.value, "ABCDEF0123456789", "Update of key value failed"
        )

        # cleanup
        KeyValuePairModelTestCase._delete([retrieved])
        try:
            retrieved = KeyValuePair.get_by_name(saved.name)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, "managed to retrieve after failure.")

    @staticmethod
    def _create_save_kvp():
        created = KeyValuePairDB(name="token", value="0123456789ABCDEF")
        return KeyValuePair.add_or_update(created)

    @staticmethod
    def _delete(model_objects):
        global SKIP_DELETE
        if SKIP_DELETE:
            return
        for model_object in model_objects:
            model_object.delete()
