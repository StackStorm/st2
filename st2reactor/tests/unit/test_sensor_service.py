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
import unittest

from oslo_config import cfg

from st2reactor.container.sensor_wrapper import SensorService
from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.constants.keyvalue import USER_SCOPE

__all__ = ["SensorServiceTestCase"]

# This trigger has schema that uses all property types
TEST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "age": {"type": "integer"},
        "name": {"type": "string", "required": True},
        "address": {"type": "string", "default": "-"},
        "career": {"type": "array"},
        "married": {"type": "boolean"},
        "awards": {"type": "object"},
        "income": {"anyOf": [{"type": "integer"}, {"type": "string"}]},
    },
}


class TriggerTypeDBMock(object):
    def __init__(self, schema=None):
        self.payload_schema = schema or {}


class TriggerDBMock(object):
    def __init__(self, type=None):
        self.type = type


class SensorServiceTestCase(unittest.TestCase):
    def setUp(self):
        def side_effect(trigger, payload, trace_context):
            self._dispatched_count += 1

        self.sensor_service = SensorService(mock.MagicMock())
        self.sensor_service._trigger_dispatcher_service._dispatcher = mock.Mock()
        self.sensor_service._trigger_dispatcher_service._dispatcher.dispatch = (
            mock.MagicMock(side_effect=side_effect)
        )
        self._dispatched_count = 0

        # Previously, cfg.CONF.system.validate_trigger_payload was set to False explicitly
        # here. Instead, we store original value so that the default is used, and if unit
        # test modifies this, we can set it to what it was (preserve test atomicity)
        self.validate_trigger_payload = cfg.CONF.system.validate_trigger_payload

    def tearDown(self):
        # Replace original configured value for payload validation
        cfg.CONF.system.validate_trigger_payload = self.validate_trigger_payload

    @mock.patch(
        "st2common.services.triggers.get_trigger_type_db",
        mock.MagicMock(return_value=TriggerTypeDBMock(TEST_SCHEMA)),
    )
    def test_dispatch_success_valid_payload_validation_enabled(self):
        cfg.CONF.system.validate_trigger_payload = True

        # define a valid payload
        payload = {
            "name": "John Doe",
            "age": 25,
            "career": ["foo, Inc.", "bar, Inc."],
            "married": True,
            "awards": {"2016": ["hoge prize", "fuga prize"]},
            "income": 50000,
        }

        # dispatching a trigger
        self.sensor_service.dispatch("trigger-name", payload)

        # This assumed that the target tirgger dispatched
        self.assertEqual(self._dispatched_count, 1)

    @mock.patch(
        "st2common.services.triggers.get_trigger_type_db",
        mock.MagicMock(return_value=TriggerTypeDBMock(TEST_SCHEMA)),
    )
    @mock.patch(
        "st2common.services.triggers.get_trigger_db_by_ref",
        mock.MagicMock(return_value=TriggerDBMock(type="trigger-type-ref")),
    )
    def test_dispatch_success_with_validation_enabled_trigger_reference(self):
        # Test a scenario where a Trigger ref and not TriggerType ref is provided
        cfg.CONF.system.validate_trigger_payload = True

        # define a valid payload
        payload = {
            "name": "John Doe",
            "age": 25,
            "career": ["foo, Inc.", "bar, Inc."],
            "married": True,
            "awards": {"2016": ["hoge prize", "fuga prize"]},
            "income": 50000,
        }

        self.assertEqual(self._dispatched_count, 0)

        # dispatching a trigger
        self.sensor_service.dispatch(
            "pack.86582f21-1fbc-44ea-88cb-0cd2b610e93b", payload
        )

        # This assumed that the target tirgger dispatched
        self.assertEqual(self._dispatched_count, 1)

    @mock.patch(
        "st2common.services.triggers.get_trigger_type_db",
        mock.MagicMock(return_value=TriggerTypeDBMock(TEST_SCHEMA)),
    )
    def test_dispatch_success_with_validation_disabled_and_invalid_payload(self):
        """
        Tests that an invalid payload still results in dispatch success with default config

        The previous config defition used StrOpt instead of BoolOpt for
        cfg.CONF.system.validate_trigger_payload. This meant that even though the intention
        was to bypass validation, the fact that this option was a string, meant it always
        resulted in True during conditionals.the

        However, the other unit tests directly modified
        cfg.CONF.system.validate_trigger_payload before running, which
        obscured this bug during testing.

        This test (as well as resetting cfg.CONF.system.validate_trigger_payload
        to it's original value during tearDown) will test validation does
        NOT take place with the default configuration.
        """
        cfg.CONF.system.validate_trigger_payload = False

        # define a invalid payload (the type of 'age' is incorrect)
        payload = {
            "name": "John Doe",
            "age": "25",
        }

        self.sensor_service.dispatch("trigger-name", payload)

        # The default config is to disable validation. So, we want to make sure
        # the dispatch actually went through.
        self.assertEqual(self._dispatched_count, 1)

    @mock.patch(
        "st2common.services.triggers.get_trigger_type_db",
        mock.MagicMock(return_value=TriggerTypeDBMock(TEST_SCHEMA)),
    )
    def test_dispatch_failure_caused_by_incorrect_type(self):
        # define a invalid payload (the type of 'age' is incorrect)
        payload = {
            "name": "John Doe",
            "age": "25",
        }

        # set config to stop dispatching when the payload comply with target trigger_type
        cfg.CONF.system.validate_trigger_payload = True

        self.sensor_service.dispatch("trigger-name", payload)

        # This assumed that the target trigger isn't dispatched
        self.assertEqual(self._dispatched_count, 0)

        # reset config to permit force dispatching
        cfg.CONF.system.validate_trigger_payload = False

        self.sensor_service.dispatch("trigger-name", payload)
        self.assertEqual(self._dispatched_count, 1)

    @mock.patch(
        "st2common.services.triggers.get_trigger_type_db",
        mock.MagicMock(return_value=TriggerTypeDBMock(TEST_SCHEMA)),
    )
    def test_dispatch_failure_caused_by_lack_of_required_parameter(self):
        # define a invalid payload (lack of required property)
        payload = {
            "age": 25,
        }
        cfg.CONF.system.validate_trigger_payload = True

        self.sensor_service.dispatch("trigger-name", payload)
        self.assertEqual(self._dispatched_count, 0)

        # reset config to permit force dispatching
        cfg.CONF.system.validate_trigger_payload = False

        self.sensor_service.dispatch("trigger-name", payload)
        self.assertEqual(self._dispatched_count, 1)

    @mock.patch(
        "st2common.services.triggers.get_trigger_type_db",
        mock.MagicMock(return_value=TriggerTypeDBMock(TEST_SCHEMA)),
    )
    def test_dispatch_failure_caused_by_extra_parameter(self):
        # define a invalid payload ('hobby' is extra)
        payload = {
            "name": "John Doe",
            "hobby": "programming",
        }
        cfg.CONF.system.validate_trigger_payload = True

        self.sensor_service.dispatch("trigger-name", payload)
        self.assertEqual(self._dispatched_count, 0)

    @mock.patch(
        "st2common.services.triggers.get_trigger_type_db",
        mock.MagicMock(return_value=TriggerTypeDBMock(TEST_SCHEMA)),
    )
    def test_dispatch_success_with_multiple_type_value(self):
        payload = {
            "name": "John Doe",
            "income": 1234,
        }

        cfg.CONF.system.validate_trigger_payload = True

        self.sensor_service.dispatch("trigger-name", payload)

        # reset payload which can have different type
        payload["income"] = "secret"

        self.sensor_service.dispatch("trigger-name", payload)
        self.assertEqual(self._dispatched_count, 2)

    @mock.patch(
        "st2common.services.triggers.get_trigger_type_db",
        mock.MagicMock(return_value=TriggerTypeDBMock(TEST_SCHEMA)),
    )
    def test_dispatch_success_with_null(self):
        payload = {
            "name": "John Doe",
            "age": None,
        }

        cfg.CONF.system.validate_trigger_payload = True

        self.sensor_service.dispatch("trigger-name", payload)
        self.assertEqual(self._dispatched_count, 1)

    @mock.patch(
        "st2common.services.triggers.get_trigger_type_db",
        mock.MagicMock(return_value=TriggerTypeDBMock()),
    )
    def test_dispatch_success_without_payload_schema(self):
        # the case trigger has no property
        self.sensor_service.dispatch("trigger-name", {})
        self.assertEqual(self._dispatched_count, 1)

    @mock.patch(
        "st2common.services.triggers.get_trigger_type_db",
        mock.MagicMock(return_value=None),
    )
    def test_dispatch_trigger_type_not_in_db_should_not_dispatch(self):
        cfg.CONF.system.validate_trigger_payload = True

        self.sensor_service.dispatch("not-in-database-ref", {})
        self.assertEqual(self._dispatched_count, 0)

    def test_datastore_methods(self):
        self.sensor_service._datastore_service = mock.Mock()

        # Verify methods take encrypt, decrypt and scope arguments
        self.sensor_service.get_value(name="foo1", scope=SYSTEM_SCOPE, decrypt=True)

        call_kwargs = self.sensor_service.datastore_service.get_value.call_args[1]
        expected_kwargs = {
            "name": "foo1",
            "local": True,
            "scope": SYSTEM_SCOPE,
            "decrypt": True,
        }
        self.assertEqual(call_kwargs, expected_kwargs)

        self.sensor_service.set_value(
            name="foo2", value="bar", scope=USER_SCOPE, encrypt=True
        )

        call_kwargs = self.sensor_service.datastore_service.set_value.call_args[1]
        expected_kwargs = {
            "name": "foo2",
            "value": "bar",
            "ttl": None,
            "local": True,
            "scope": USER_SCOPE,
            "encrypt": True,
        }
        self.assertEqual(call_kwargs, expected_kwargs)

        self.sensor_service.delete_value(name="foo3", scope=USER_SCOPE)

        call_kwargs = self.sensor_service.datastore_service.delete_value.call_args[1]
        expected_kwargs = {"name": "foo3", "local": True, "scope": USER_SCOPE}
        self.assertEqual(call_kwargs, expected_kwargs)
