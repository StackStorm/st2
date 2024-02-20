#!/usr/bin/env python

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

from oslo_config import cfg

from st2common.util.monkey_patch import use_select_poll_workaround

use_select_poll_workaround()

from st2common.content.bootstrap import register_content
from st2common.persistence.pack import Pack
from st2common.persistence.pack import Config
from st2common.persistence.pack import ConfigSchema
from st2common.persistence.actionalias import ActionAlias
from st2common.persistence.action import Action
from st2common.persistence.rule import Rule
from st2common.persistence.policy import Policy
from st2common.persistence.sensor import SensorType as Sensor
from st2common.persistence.trigger import TriggerType

from st2tests.base import BaseActionTestCase
from st2tests.base import CleanDbTestCase
from st2tests.fixtures.packs.dummy_pack_1.fixture import (
    PACK_NAME as DUMMY_PACK_1,
    PACK_PATH as PACK_PATH_1,
)

from pack_mgmt.unload import UnregisterPackAction

__all__ = ["UnloadActionTestCase"]


class UnloadActionTestCase(BaseActionTestCase, CleanDbTestCase):
    action_cls = UnregisterPackAction

    def setUp(self):
        super(UnloadActionTestCase, self).setUp()

        # Register mock pack
        # Verify DB is empty
        pack_dbs = Pack.get_all()
        config_schema_dbs = ConfigSchema.get_all()
        config_dbs = Config.get_all()

        self.assertEqual(len(pack_dbs), 0)
        self.assertEqual(len(config_schema_dbs), 0)
        self.assertEqual(len(config_dbs), 0)

        # Register the pack with all the content
        # TODO: Don't use pack cache
        cfg.CONF.set_override(name="all", override=True, group="register")
        cfg.CONF.set_override(name="pack", override=PACK_PATH_1, group="register")
        cfg.CONF.set_override(
            name="no_fail_on_failure", override=True, group="register"
        )
        register_content()

    def test_run(self):
        pack = DUMMY_PACK_1
        # Verify all the resources are there

        pack_dbs = Pack.query(ref=pack)
        action_dbs = Action.query(pack=pack)
        alias_dbs = ActionAlias.query(pack=pack)
        rule_dbs = Rule.query(pack=pack)
        sensor_dbs = Sensor.query(pack=pack)
        trigger_type_dbs = TriggerType.query(pack=pack)
        policy_dbs = Policy.query(pack=pack)

        config_schema_dbs = ConfigSchema.query(pack=pack)
        config_dbs = Config.query(pack=pack)

        self.assertEqual(len(pack_dbs), 1)
        self.assertEqual(len(action_dbs), 3)
        self.assertEqual(len(alias_dbs), 3)
        self.assertEqual(len(rule_dbs), 1)
        self.assertEqual(len(sensor_dbs), 3)
        self.assertEqual(len(trigger_type_dbs), 4)
        self.assertEqual(len(policy_dbs), 2)

        self.assertEqual(len(config_schema_dbs), 1)
        self.assertEqual(len(config_dbs), 1)

        # Run action
        action = self.get_action_instance()
        action.run(packs=[pack])

        # Make sure all resources have been removed from the db
        pack_dbs = Pack.query(ref=pack)
        action_dbs = Action.query(pack=pack)
        alias_dbs = ActionAlias.query(pack=pack)
        rule_dbs = Rule.query(pack=pack)
        sensor_dbs = Sensor.query(pack=pack)
        trigger_type_dbs = TriggerType.query(pack=pack)
        policy_dbs = Policy.query(pack=pack)

        config_schema_dbs = ConfigSchema.query(pack=pack)
        config_dbs = Config.query(pack=pack)

        self.assertEqual(len(pack_dbs), 0)
        self.assertEqual(len(action_dbs), 0)
        self.assertEqual(len(alias_dbs), 0)
        self.assertEqual(len(rule_dbs), 0)
        self.assertEqual(len(sensor_dbs), 0)
        self.assertEqual(len(trigger_type_dbs), 0)
        self.assertEqual(len(policy_dbs), 0)

        self.assertEqual(len(config_schema_dbs), 0)
        self.assertEqual(len(config_dbs), 0)
