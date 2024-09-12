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

from __future__ import absolute_import
import unittest

from st2common.util.payload import PayloadLookup
import st2tests.config as tests_config

__all__ = ["PayloadLookupTestCase"]


class PayloadLookupTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = PayloadLookup(
            {
                "pikachu": "Has no ears",
                "charmander": "Plays with fire",
            }
        )
        super(PayloadLookupTestCase, cls).setUpClass()
        tests_config.parse_args()

    def test_get_key(self):
        self.assertEqual(self.payload.get_value("trigger.pikachu"), ["Has no ears"])
        self.assertEqual(
            self.payload.get_value("trigger.charmander"), ["Plays with fire"]
        )

    def test_explicitly_get_multiple_keys(self):
        self.assertEqual(self.payload.get_value("trigger.pikachu[*]"), ["Has no ears"])
        self.assertEqual(
            self.payload.get_value("trigger.charmander[*]"), ["Plays with fire"]
        )

    def test_get_nonexistent_key(self):
        self.assertIsNone(self.payload.get_value("trigger.squirtle"))
