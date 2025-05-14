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
import json
import hashlib
from collections import OrderedDict
import sys

# TODO: Move keywords directly to hashlib.md5 call as part of dropping py3.8.
hashlib_kwargs = {} if sys.version_info[0:2] < (3, 9) else {"usedforsecurity": False}

import unittest

from st2common.models.db.pack import PackDB
from st2common.models.db.sensor import SensorTypeDB
from st2common.models.db.action import ActionDB
from st2common.models.db.rule import RuleDB
from st2common.models.db.trigger import TriggerTypeDB
from st2common.models.db.trigger import TriggerDB
from st2common.models.db.policy import PolicyTypeDB
from st2common.models.db.policy import PolicyDB
from st2common.models.db.auth import ApiKeyDB

__all__ = ["DBModelUIDFieldTestCase"]


class DBModelUIDFieldTestCase(unittest.TestCase):
    def test_get_uid(self):
        pack_db = PackDB(ref="ma_pack")
        self.assertEqual(pack_db.get_uid(), "pack:ma_pack")
        self.assertTrue(pack_db.has_valid_uid())

        sensor_type_db = SensorTypeDB(name="sname", pack="spack")
        self.assertEqual(sensor_type_db.get_uid(), "sensor_type:spack:sname")
        self.assertTrue(sensor_type_db.has_valid_uid())

        action_db = ActionDB(name="aname", pack="apack", runner_type={})
        self.assertEqual(action_db.get_uid(), "action:apack:aname")
        self.assertTrue(action_db.has_valid_uid())

        rule_db = RuleDB(name="rname", pack="rpack")
        self.assertEqual(rule_db.get_uid(), "rule:rpack:rname")
        self.assertTrue(rule_db.has_valid_uid())

        trigger_type_db = TriggerTypeDB(name="ttname", pack="ttpack")
        self.assertEqual(trigger_type_db.get_uid(), "trigger_type:ttpack:ttname")
        self.assertTrue(trigger_type_db.has_valid_uid())

        trigger_db = TriggerDB(name="tname", pack="tpack")
        self.assertTrue(trigger_db.get_uid().startswith("trigger:tpack:tname:"))

        # Verify that same set of parameters always results in the same hash
        parameters = {"a": 1, "b": "unicode", "c": [1, 2, 3], "d": {"g": 1, "h": 2}}
        paramers_hash = json.dumps(parameters, sort_keys=True)
        paramers_hash = hashlib.md5(
            paramers_hash.encode(), **hashlib_kwargs
        ).hexdigest()  # nosec. remove nosec after py3.8 drop

        parameters = {"a": 1, "b": "unicode", "c": [1, 2, 3], "d": {"g": 1, "h": 2}}
        trigger_db = TriggerDB(name="tname", pack="tpack", parameters=parameters)
        self.assertEqual(
            trigger_db.get_uid(), "trigger:tpack:tname:%s" % (paramers_hash)
        )
        self.assertTrue(trigger_db.has_valid_uid())

        parameters = {"c": [1, 2, 3], "b": "unicode", "d": {"h": 2, "g": 1}, "a": 1}
        trigger_db = TriggerDB(name="tname", pack="tpack", parameters=parameters)
        self.assertEqual(
            trigger_db.get_uid(), "trigger:tpack:tname:%s" % (paramers_hash)
        )
        self.assertTrue(trigger_db.has_valid_uid())

        parameters = {"b": "unicode", "c": [1, 2, 3], "d": {"h": 2, "g": 1}, "a": 1}
        trigger_db = TriggerDB(name="tname", pack="tpack", parameters=parameters)
        self.assertEqual(
            trigger_db.get_uid(), "trigger:tpack:tname:%s" % (paramers_hash)
        )
        self.assertTrue(trigger_db.has_valid_uid())

        parameters = OrderedDict(
            {"c": [1, 2, 3], "b": "unicode", "d": {"h": 2, "g": 1}, "a": 1}
        )
        trigger_db = TriggerDB(name="tname", pack="tpack", parameters=parameters)
        self.assertEqual(
            trigger_db.get_uid(), "trigger:tpack:tname:%s" % (paramers_hash)
        )
        self.assertTrue(trigger_db.has_valid_uid())

        policy_type_db = PolicyTypeDB(resource_type="action", name="concurrency")
        self.assertEqual(policy_type_db.get_uid(), "policy_type:action:concurrency")
        self.assertTrue(policy_type_db.has_valid_uid())

        policy_db = PolicyDB(pack="dummy", name="policy1")
        self.assertEqual(policy_db.get_uid(), "policy:dummy:policy1")

        api_key_db = ApiKeyDB(key_hash="valid")
        self.assertEqual(api_key_db.get_uid(), "api_key:valid")
        self.assertTrue(api_key_db.has_valid_uid())

        api_key_db = ApiKeyDB()
        self.assertEqual(api_key_db.get_uid(), "api_key:")
        self.assertFalse(api_key_db.has_valid_uid())
