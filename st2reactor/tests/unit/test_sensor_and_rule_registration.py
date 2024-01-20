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

import mock

from st2tests import DbTestCase
from st2common.persistence.rule import Rule
from st2common.persistence.sensor import SensorType
from st2common.persistence.trigger import Trigger
from st2common.persistence.trigger import TriggerType
from st2common.transport.publishers import PoolPublisher
from st2common.bootstrap.sensorsregistrar import SensorsRegistrar
from st2common.bootstrap.rulesregistrar import RulesRegistrar

from tests.fixtures.packs import PACKS_DIR
from tests.fixtures.packs.pack_with_rules.fixture import (
    PACK_PATH as PACK_WITH_RULES_PATH,
)
from tests.fixtures.packs.pack_with_sensor.fixture import (
    PACK_PATH as PACK_WITH_SENSOR_PATH,
)

__all__ = ["SensorRegistrationTestCase", "RuleRegistrationTestCase"]


# NOTE: We need to perform this patching because test fixtures are located outside of the packs
# base paths directory. This will never happen outside the context of test fixtures.
@mock.patch(
    "st2common.content.utils.get_pack_base_path",
    mock.Mock(return_value=PACK_WITH_SENSOR_PATH),
)
class SensorRegistrationTestCase(DbTestCase):
    @mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
    def test_register_sensors(self):
        # Verify DB is empty at the beginning
        self.assertEqual(len(SensorType.get_all()), 0)
        self.assertEqual(len(TriggerType.get_all()), 0)
        self.assertEqual(len(Trigger.get_all()), 0)

        registrar = SensorsRegistrar()
        registrar.register_from_packs(base_dirs=[PACKS_DIR])

        # Verify objects have been created
        sensor_dbs = SensorType.get_all()
        trigger_type_dbs = TriggerType.get_all()
        trigger_dbs = Trigger.get_all()

        self.assertEqual(len(sensor_dbs), 2)
        self.assertEqual(len(trigger_type_dbs), 2)
        self.assertEqual(len(trigger_dbs), 2)

        self.assertEqual(sensor_dbs[0].name, "TestSensor")
        self.assertEqual(sensor_dbs[0].poll_interval, 10)
        self.assertTrue(sensor_dbs[0].enabled)
        self.assertEqual(sensor_dbs[0].metadata_file, "sensors/test_sensor_1.yaml")

        self.assertEqual(sensor_dbs[1].name, "TestSensorDisabled")
        self.assertEqual(sensor_dbs[1].poll_interval, 10)
        self.assertFalse(sensor_dbs[1].enabled)
        self.assertEqual(sensor_dbs[1].metadata_file, "sensors/test_sensor_2.yaml")

        self.assertEqual(trigger_type_dbs[0].name, "trigger_type_1")
        self.assertEqual(trigger_type_dbs[0].pack, "pack_with_sensor")
        self.assertEqual(len(trigger_type_dbs[0].tags), 0)
        self.assertEqual(trigger_type_dbs[1].name, "trigger_type_2")
        self.assertEqual(trigger_type_dbs[1].pack, "pack_with_sensor")
        self.assertEqual(len(trigger_type_dbs[1].tags), 2)
        self.assertEqual(trigger_type_dbs[1].tags[0].name, "tag1name")
        self.assertEqual(trigger_type_dbs[1].tags[0].value, "tag1 value")

        # Triggered which are registered via sensors have metadata_file pointing to the sensor
        # definition file
        self.assertEqual(
            trigger_type_dbs[0].metadata_file, "sensors/test_sensor_1.yaml"
        )
        self.assertEqual(
            trigger_type_dbs[1].metadata_file, "sensors/test_sensor_1.yaml"
        )

        # Verify second call to registration doesn't create a duplicate objects
        registrar.register_from_packs(base_dirs=[PACKS_DIR])

        sensor_dbs = SensorType.get_all()
        trigger_type_dbs = TriggerType.get_all()
        trigger_dbs = Trigger.get_all()

        self.assertEqual(len(sensor_dbs), 2)
        self.assertEqual(len(trigger_type_dbs), 2)
        self.assertEqual(len(trigger_dbs), 2)

        self.assertEqual(sensor_dbs[0].name, "TestSensor")
        self.assertEqual(sensor_dbs[0].poll_interval, 10)

        self.assertEqual(trigger_type_dbs[0].name, "trigger_type_1")
        self.assertEqual(trigger_type_dbs[0].pack, "pack_with_sensor")
        self.assertEqual(trigger_type_dbs[1].name, "trigger_type_2")
        self.assertEqual(trigger_type_dbs[1].pack, "pack_with_sensor")

        # Verify sensor and trigger data is updated on registration
        original_load = registrar._meta_loader.load

        def mock_load(*args, **kwargs):
            # Update poll_interval and trigger_type_2 description
            data = original_load(*args, **kwargs)
            data["poll_interval"] = 50
            data["trigger_types"][1]["description"] = "test 2"
            return data

        registrar._meta_loader.load = mock_load

        registrar.register_from_packs(base_dirs=[PACKS_DIR])

        sensor_dbs = SensorType.get_all()
        trigger_type_dbs = TriggerType.get_all()
        trigger_dbs = Trigger.get_all()

        self.assertEqual(len(sensor_dbs), 2)
        self.assertEqual(len(trigger_type_dbs), 2)
        self.assertEqual(len(trigger_dbs), 2)

        self.assertEqual(sensor_dbs[0].name, "TestSensor")
        self.assertEqual(sensor_dbs[0].poll_interval, 50)

        self.assertEqual(trigger_type_dbs[0].name, "trigger_type_1")
        self.assertEqual(trigger_type_dbs[0].pack, "pack_with_sensor")
        self.assertEqual(trigger_type_dbs[1].name, "trigger_type_2")
        self.assertEqual(trigger_type_dbs[1].pack, "pack_with_sensor")
        self.assertEqual(trigger_type_dbs[1].description, "test 2")


# NOTE: We need to perform this patching because test fixtures are located outside of the packs
# base paths directory. This will never happen outside the context of test fixtures.
@mock.patch(
    "st2common.content.utils.get_pack_base_path",
    mock.Mock(return_value=PACK_WITH_RULES_PATH),
)
class RuleRegistrationTestCase(DbTestCase):
    def test_register_rules(self):
        # Verify DB is empty at the beginning
        self.assertEqual(len(Rule.get_all()), 0)
        self.assertEqual(len(Trigger.get_all()), 0)

        registrar = RulesRegistrar()
        registrar.register_from_packs(base_dirs=[PACKS_DIR])

        # Verify modeles are created
        rule_dbs = Rule.get_all()
        trigger_dbs = Trigger.get_all()
        self.assertEqual(len(rule_dbs), 2)
        self.assertEqual(len(trigger_dbs), 1)

        self.assertEqual(rule_dbs[0].name, "sample.with_the_same_timer")
        self.assertEqual(rule_dbs[1].name, "sample.with_timer")
        self.assertIsNotNone(trigger_dbs[0].name)

        # Verify second register call updates existing models
        registrar.register_from_packs(base_dirs=[PACKS_DIR])

        rule_dbs = Rule.get_all()
        trigger_dbs = Trigger.get_all()
        self.assertEqual(len(rule_dbs), 2)
        self.assertEqual(len(trigger_dbs), 1)
