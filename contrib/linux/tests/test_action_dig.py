#!/usr/bin/env python

# Copyright 2020 The StackStorm Authors.
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
from st2tests.base import BaseActionTestCase

from dig import DigAction


class DigActionTestCase(BaseActionTestCase):
    action_cls = DigAction

    def test_run_with_empty_hostname(self):
        action = self.get_action_instance()

        # Use the defaults from dig.yaml
        result = action.run(
            rand=False,
            count=0,
            nameserver=None,
            hostname="",
            queryopts="short",
            querytype="",
        )
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_run_with_empty_queryopts(self):
        action = self.get_action_instance()

        results = action.run(
            rand=False,
            count=0,
            nameserver=None,
            hostname="google.com",
            queryopts="",
            querytype="",
        )
        self.assertIsInstance(results, list)

        for result in results:
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_run_with_empty_querytype(self):
        action = self.get_action_instance()

        results = action.run(
            rand=False,
            count=0,
            nameserver=None,
            hostname="google.com",
            queryopts="short",
            querytype="",
        )
        self.assertIsInstance(results, list)

        for result in results:
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_run(self):
        action = self.get_action_instance()

        results = action.run(
            rand=False,
            count=0,
            nameserver=None,
            hostname="google.com",
            queryopts="short",
            querytype="A",
        )
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

        for result in results:
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
