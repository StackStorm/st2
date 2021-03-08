# -*- coding: utf-8 -*-

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
from integration.orquesta import base
from st2client import models
from st2common.constants import action as ac_const


class DatastoreFunctionTest(base.TestWorkflowExecution):
    @classmethod
    def set_kvp(cls, name, value, scope="system", secret=False):
        kvp = models.KeyValuePair(
            id=name, name=name, value=value, scope=scope, secret=secret
        )

        cls.st2client.keys.update(kvp)

    @classmethod
    def del_kvp(cls, name, scope="system"):
        kvp = models.KeyValuePair(id=name, name=name, scope=scope)

        cls.st2client.keys.delete(kvp)

    def test_st2kv_system_scope(self):
        key = "lakshmi"
        value = "kanahansnasnasdlsajks"

        self.set_kvp(key, value)
        wf_name = "examples.orquesta-st2kv"
        wf_input = {"key_name": "system.%s" % key}
        execution = self._execute_workflow(wf_name, wf_input)

        output = self._wait_for_completion(execution)

        self.assertEqual(output.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn("output", output.result)
        self.assertIn("value", output.result["output"])
        self.assertEqual(value, output.result["output"]["value"])
        self.del_kvp(key)

    def test_st2kv_user_scope(self):
        key = "winson"
        value = "SoDiamondEng"

        self.set_kvp(key, value, "user")
        wf_name = "examples.orquesta-st2kv"
        wf_input = {"key_name": key}
        execution = self._execute_workflow(wf_name, wf_input)

        output = self._wait_for_completion(execution)

        self.assertEqual(output.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn("output", output.result)
        self.assertIn("value", output.result["output"])
        self.assertEqual(value, output.result["output"]["value"])
        # self.del_kvp(key)

    def test_st2kv_decrypt(self):
        key = "kami"
        value = "eggplant"

        self.set_kvp(key, value, secret=True)
        wf_name = "examples.orquesta-st2kv"
        wf_input = {"key_name": "system.%s" % key, "decrypt": True}

        execution = self._execute_workflow(wf_name, wf_input)

        output = self._wait_for_completion(execution)

        self.assertEqual(output.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn("output", output.result)
        self.assertIn("value", output.result["output"])
        self.assertEqual(value, output.result["output"]["value"])
        self.del_kvp(key)

    def test_st2kv_nonexistent(self):
        key = "matt"

        wf_name = "examples.orquesta-st2kv"
        wf_input = {"key_name": "system.%s" % key, "decrypt": True}

        execution = self._execute_workflow(wf_name, wf_input)

        output = self._wait_for_completion(execution)

        self.assertEqual(output.status, ac_const.LIVEACTION_STATUS_FAILED)

        expected_error = (
            'The key "%s" does not exist in the StackStorm datastore.' % key
        )

        self.assertIn(expected_error, output.result["errors"][0]["message"])

    def test_st2kv_default_value(self):
        key = "matt"

        wf_name = "examples.orquesta-st2kv-default"
        wf_input = {"key_name": "system.%s" % key, "decrypt": True, "default": "stone"}

        execution = self._execute_workflow(wf_name, wf_input)

        output = self._wait_for_completion(execution)

        self.assertEqual(output.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn("output", output.result)
        self.assertIn("value_from_yaql", output.result["output"])
        self.assertEqual(
            wf_input["default"], output.result["output"]["value_from_yaql"]
        )
        self.assertIn("value_from_jinja", output.result["output"])
        self.assertEqual(
            wf_input["default"], output.result["output"]["value_from_jinja"]
        )

    def test_st2kv_default_value_with_empty_string(self):
        key = "matt"

        wf_name = "examples.orquesta-st2kv-default"
        wf_input = {"key_name": "system.%s" % key, "decrypt": True, "default": ""}

        execution = self._execute_workflow(wf_name, wf_input)

        output = self._wait_for_completion(execution)

        self.assertEqual(output.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn("output", output.result)
        self.assertIn("value_from_yaql", output.result["output"])
        self.assertEqual(
            wf_input["default"], output.result["output"]["value_from_yaql"]
        )
        self.assertIn("value_from_jinja", output.result["output"])
        self.assertEqual(
            wf_input["default"], output.result["output"]["value_from_jinja"]
        )

    def test_st2kv_default_value_with_null(self):
        key = "matt"

        wf_name = "examples.orquesta-st2kv-default"
        wf_input = {"key_name": "system.%s" % key, "decrypt": True, "default": None}

        execution = self._execute_workflow(wf_name, wf_input)

        output = self._wait_for_completion(execution)

        self.assertEqual(output.status, ac_const.LIVEACTION_STATUS_SUCCEEDED)
        self.assertIn("output", output.result)
        self.assertIn("value_from_yaql", output.result["output"])
        self.assertEqual(
            wf_input["default"], output.result["output"]["value_from_yaql"]
        )
        self.assertIn("value_from_jinja", output.result["output"])
        self.assertEqual(
            wf_input["default"], output.result["output"]["value_from_jinja"]
        )
