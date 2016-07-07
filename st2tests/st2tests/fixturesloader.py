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

import copy
import os

import six

from st2common.content.loader import MetaLoader

from st2common.models.api.action import (ActionAPI, LiveActionAPI, ActionExecutionStateAPI,
                                         RunnerTypeAPI, ActionAliasAPI)
from st2common.models.api.auth import ApiKeyAPI, UserAPI
from st2common.models.api.execution import (ActionExecutionAPI)
from st2common.models.api.policy import (PolicyTypeAPI, PolicyAPI)
from st2common.models.api.rule import (RuleAPI)
from st2common.models.api.rule_enforcement import RuleEnforcementAPI
from st2common.models.api.sensor import SensorTypeAPI
from st2common.models.api.trace import TraceAPI
from st2common.models.api.trigger import (TriggerAPI, TriggerTypeAPI, TriggerInstanceAPI)

from st2common.models.db.action import ActionDB
from st2common.models.db.actionalias import ActionAliasDB
from st2common.models.db.auth import ApiKeyDB, UserDB
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.executionstate import ActionExecutionStateDB
from st2common.models.db.runner import RunnerTypeDB
from st2common.models.db.execution import (ActionExecutionDB)
from st2common.models.db.policy import (PolicyTypeDB, PolicyDB)
from st2common.models.db.rule import RuleDB
from st2common.models.db.rule_enforcement import RuleEnforcementDB
from st2common.models.db.sensor import SensorTypeDB
from st2common.models.db.trace import TraceDB
from st2common.models.db.trigger import (TriggerDB, TriggerTypeDB, TriggerInstanceDB)
from st2common.persistence.action import Action
from st2common.persistence.actionalias import ActionAlias
from st2common.persistence.execution import ActionExecution
from st2common.persistence.executionstate import ActionExecutionState
from st2common.persistence.auth import ApiKey, User
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.runner import RunnerType
from st2common.persistence.policy import (PolicyType, Policy)
from st2common.persistence.rule import Rule
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.persistence.sensor import SensorType
from st2common.persistence.trace import Trace
from st2common.persistence.trigger import (Trigger, TriggerType, TriggerInstance)


ALLOWED_DB_FIXTURES = ['actions', 'actionstates', 'aliases', 'executions', 'liveactions',
                       'policies', 'policytypes', 'rules', 'runners', 'sensors',
                       'triggertypes', 'triggers', 'triggerinstances', 'traces', 'apikeys',
                       'users', 'enforcements']
ALLOWED_FIXTURES = copy.copy(ALLOWED_DB_FIXTURES)
ALLOWED_FIXTURES.extend(['actionchains', 'workflows'])

FIXTURE_DB_MODEL = {
    'actions': ActionDB,
    'aliases': ActionAliasDB,
    'actionstates': ActionExecutionStateDB,
    'apikeys': ApiKeyDB,
    'enforcements': RuleEnforcementDB,
    'executions': ActionExecutionDB,
    'liveactions': LiveActionDB,
    'policies': PolicyDB,
    'policytypes': PolicyTypeDB,
    'rules': RuleDB,
    'runners': RunnerTypeDB,
    'sensors': SensorTypeDB,
    'traces': TraceDB,
    'triggertypes': TriggerTypeDB,
    'triggers': TriggerDB,
    'triggerinstances': TriggerInstanceDB,
    'users': UserDB
}

FIXTURE_API_MODEL = {
    'actions': ActionAPI,
    'aliases': ActionAliasAPI,
    'actionstates': ActionExecutionStateAPI,
    'apikeys': ApiKeyAPI,
    'enforcements': RuleEnforcementAPI,
    'executions': ActionExecutionAPI,
    'liveactions': LiveActionAPI,
    'policies': PolicyAPI,
    'policytypes': PolicyTypeAPI,
    'rules': RuleAPI,
    'runners': RunnerTypeAPI,
    'sensors': SensorTypeAPI,
    'traces': TraceAPI,
    'triggertypes': TriggerTypeAPI,
    'triggers': TriggerAPI,
    'triggerinstances': TriggerInstanceAPI,
    'users': UserAPI
}


FIXTURE_PERSISTENCE_MODEL = {
    'actions': Action,
    'aliases': ActionAlias,
    'actionstates': ActionExecutionState,
    'apikeys': ApiKey,
    'enforcements': RuleEnforcement,
    'executions': ActionExecution,
    'liveactions': LiveAction,
    'policies': Policy,
    'policytypes': PolicyType,
    'rules': Rule,
    'runners': RunnerType,
    'sensors': SensorType,
    'traces': Trace,
    'triggertypes': TriggerType,
    'triggers': Trigger,
    'triggerinstances': TriggerInstance,
    'users': User
}


def get_fixtures_base_path():
    return os.path.join(os.path.dirname(__file__), 'fixtures')


def get_fixtures_packs_base_path():
    return os.path.join(os.path.dirname(__file__), 'fixtures/packs')


def get_resources_base_path():
    return os.path.join(os.path.dirname(__file__), 'resources')


class FixturesLoader(object):
    def __init__(self):
        self.meta_loader = MetaLoader()

    def save_fixtures_to_db(self, fixtures_pack='generic', fixtures_dict=None):
        """
        Loads fixtures specified in fixtures_dict into the database
        and returns DB models for the fixtures.

        fixtures_dict should be of the form:
        {
            'actions': ['action-1.yaml', 'action-2.yaml'],
            'rules': ['rule-1.yaml'],
            'liveactions': ['execution-1.yaml']
        }

        :param fixtures_pack: Name of the pack to load fixtures from.
        :type fixtures_pack: ``str``

        :param fixtures_dict: Dictionary specifying the fixtures to load for each type.
        :type fixtures_dict: ``dict``

        :rtype: ``dict``
        """
        if fixtures_dict is None:
            fixtures_dict = {}
        fixtures_pack_path = self._validate_fixtures_pack(fixtures_pack)
        self._validate_fixture_dict(fixtures_dict, allowed=ALLOWED_DB_FIXTURES)

        db_models = {}
        for fixture_type, fixtures in six.iteritems(fixtures_dict):
            API_MODEL = FIXTURE_API_MODEL.get(fixture_type, None)
            PERSISTENCE_MODEL = FIXTURE_PERSISTENCE_MODEL.get(fixture_type, None)

            loaded_fixtures = {}
            for fixture in fixtures:
                # Guard against copy and type and similar typos
                if fixture in loaded_fixtures:
                    msg = 'Fixture "%s" is specified twice, probably a typo.' % (fixture)
                    raise ValueError(msg)

                fixture_dict = self.meta_loader.load(
                    self._get_fixture_file_path_abs(fixtures_pack_path, fixture_type, fixture))
                api_model = API_MODEL(**fixture_dict)
                db_model = API_MODEL.to_model(api_model)
                db_model = PERSISTENCE_MODEL.add_or_update(db_model)
                loaded_fixtures[fixture] = db_model

            db_models[fixture_type] = loaded_fixtures

        return db_models

    def load_fixtures(self, fixtures_pack='generic', fixtures_dict=None):
        """
        Loads fixtures specified in fixtures_dict. We
        simply want to load the meta into dict objects.

        fixtures_dict should be of the form:
        {
            'actionchains': ['actionchain1.yaml', 'actionchain2.yaml'],
            'workflows': ['workflow.yaml']
        }

        :param fixtures_pack: Name of the pack to load fixtures from.
        :type fixtures_pack: ``str``

        :param fixtures_dict: Dictionary specifying the fixtures to load for each type.
        :type fixtures_dict: ``dict``

        :rtype: ``dict``
        """
        if not fixtures_dict:
            return {}
        fixtures_pack_path = self._validate_fixtures_pack(fixtures_pack)
        self._validate_fixture_dict(fixtures_dict)

        all_fixtures = {}
        for fixture_type, fixtures in six.iteritems(fixtures_dict):
            loaded_fixtures = {}
            for fixture in fixtures:
                fixture_dict = self.meta_loader.load(
                    self._get_fixture_file_path_abs(fixtures_pack_path, fixture_type, fixture))
                loaded_fixtures[fixture] = fixture_dict
            all_fixtures[fixture_type] = loaded_fixtures

        return all_fixtures

    def load_models(self, fixtures_pack='generic', fixtures_dict=None):
        """
        Loads fixtures specified in fixtures_dict as db models. This method must be
        used for fixtures that have associated DB models. We simply want to load the
        meta as DB models but don't want to save them to db.

        fixtures_dict should be of the form:
        {
            'actions': ['action-1.yaml', 'action-2.yaml'],
            'rules': ['rule-1.yaml'],
            'liveactions': ['execution-1.yaml']
        }

        :param fixtures_pack: Name of the pack to load fixtures from.
        :type fixtures_pack: ``str``

        :param fixtures_dict: Dictionary specifying the fixtures to load for each type.
        :type fixtures_dict: ``dict``

        :rtype: ``dict``
        """
        if not fixtures_dict:
            return {}
        fixtures_pack_path = self._validate_fixtures_pack(fixtures_pack)
        self._validate_fixture_dict(fixtures_dict, allowed=ALLOWED_DB_FIXTURES)

        all_fixtures = {}
        for fixture_type, fixtures in six.iteritems(fixtures_dict):

            API_MODEL = FIXTURE_API_MODEL.get(fixture_type, None)

            loaded_models = {}
            for fixture in fixtures:
                fixture_dict = self.meta_loader.load(
                    self._get_fixture_file_path_abs(fixtures_pack_path, fixture_type, fixture))
                api_model = API_MODEL(**fixture_dict)
                db_model = API_MODEL.to_model(api_model)
                loaded_models[fixture] = db_model
            all_fixtures[fixture_type] = loaded_models

        return all_fixtures

    def delete_fixtures_from_db(self, fixtures_pack='generic', fixtures_dict=None,
                                raise_on_fail=False):
        """
        Deletes fixtures specified in fixtures_dict from the database.

        fixtures_dict should be of the form:
        {
            'actions': ['action-1.yaml', 'action-2.yaml'],
            'rules': ['rule-1.yaml'],
            'liveactions': ['execution-1.yaml']
        }

        :param fixtures_pack: Name of the pack to delete fixtures from.
        :type fixtures_pack: ``str``

        :param fixtures_dict: Dictionary specifying the fixtures to delete for each type.
        :type fixtures_dict: ``dict``

        :param raise_on_fail: Optional If True, raises exception if delete fails on any fixture.
        :type raise_on_fail: ``boolean``
        """
        if not fixtures_dict:
            return
        fixtures_pack_path = self._validate_fixtures_pack(fixtures_pack)
        self._validate_fixture_dict(fixtures_dict)

        for fixture_type, fixtures in six.iteritems(fixtures_dict):
            API_MODEL = FIXTURE_API_MODEL.get(fixture_type, None)
            PERSISTENCE_MODEL = FIXTURE_PERSISTENCE_MODEL.get(fixture_type, None)
            for fixture in fixtures:
                fixture_dict = self.meta_loader.load(
                    self._get_fixture_file_path_abs(fixtures_pack_path, fixture_type, fixture))
                # Note that when we have a reference mechanism consistent for
                # every model, we can just do a get and delete the object. Until
                # then, this model conversions are necessary.
                api_model = API_MODEL(**fixture_dict)
                db_model = API_MODEL.to_model(api_model)
                try:
                    PERSISTENCE_MODEL.delete(db_model)
                except:
                    if raise_on_fail:
                        raise

    def delete_models_from_db(self, models_dict, raise_on_fail=False):
        """
        Deletes models specified in models_dict from the database.

        models_dict should be of the form:
        {
            'actions': [ACTION1, ACTION2],
            'rules': [RULE1],
            'liveactions': [EXECUTION]
        }

        :param fixtures_dict: Dictionary specifying the fixtures to delete for each type.
        :type fixtures_dict: ``dict``.

        :param raise_on_fail: Optional If True, raises exception if delete fails on any model.
        :type raise_on_fail: ``boolean``
        """
        for model_type, models in six.iteritems(models_dict):
            PERSISTENCE_MODEL = FIXTURE_PERSISTENCE_MODEL.get(model_type, None)
            for model in models:
                try:
                    PERSISTENCE_MODEL.delete(model)
                except:
                    if raise_on_fail:
                        raise

    def _validate_fixtures_pack(self, fixtures_pack):
        fixtures_pack_path = self._get_fixtures_pack_path(fixtures_pack)

        if not self._is_fixture_pack_exists(fixtures_pack_path):
            raise Exception('Fixtures pack not found ' +
                            'in fixtures path %s.' % get_fixtures_base_path())
        return fixtures_pack_path

    def _validate_fixture_dict(self, fixtures_dict, allowed=ALLOWED_FIXTURES):
        fixture_types = fixtures_dict.keys()
        for fixture_type in fixture_types:
            if fixture_type not in allowed:
                raise Exception('Disallowed fixture type: %s' % fixture_type)

    def _is_fixture_pack_exists(self, fixtures_pack_path):
        return os.path.exists(fixtures_pack_path)

    def _get_fixture_file_path_abs(self, fixtures_pack_path, fixtures_type, fixture_name):
        return os.path.join(fixtures_pack_path, fixtures_type, fixture_name)

    def _get_fixtures_pack_path(self, fixtures_pack_name):
        return os.path.join(get_fixtures_base_path(), fixtures_pack_name)

    def get_fixture_file_path_abs(self, fixtures_pack, fixtures_type, fixture_name):
        return os.path.join(get_fixtures_base_path(), fixtures_pack, fixtures_type, fixture_name)
