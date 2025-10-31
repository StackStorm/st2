# coding=utf-8
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
from unittest import TestCase

from st2common.util.config_parser import ContentPackConfigParser
import st2tests.config as tests_config
from st2tests.fixtures.packs.dummy_pack_1.fixture import PACK_NAME as DUMMY_PACK_1
from st2tests.fixtures.packs.dummy_pack_2.fixture import PACK_NAME as DUMMY_PACK_2
from st2tests.fixtures.packs.dummy_pack_18.fixture import PACK_DIR_NAME as DUMMY_PACK_18


class ContentPackConfigParserTestCase(TestCase):
    def setUp(self):
        super(ContentPackConfigParserTestCase, self).setUp()
        tests_config.parse_args()

    def test_get_config_inexistent_pack(self):
        parser = ContentPackConfigParser(pack_name="inexistent")
        config = parser.get_config()
        self.assertEqual(config, None)

    def test_get_config_no_config(self):
        pack_name = DUMMY_PACK_1
        parser = ContentPackConfigParser(pack_name=pack_name)

        config = parser.get_config()
        self.assertEqual(config, None)

    def test_get_config_existing_config(self):
        pack_name = DUMMY_PACK_2
        parser = ContentPackConfigParser(pack_name=pack_name)

        config = parser.get_config()
        self.assertEqual(config.config["section1"]["key1"], "value1")
        self.assertEqual(config.config["section2"]["key10"], "value10")

    def test_get_config_for_unicode_char(self):
        pack_name = DUMMY_PACK_18
        parser = ContentPackConfigParser(pack_name=pack_name)
        config = parser.get_config()
        self.assertEqual(config.config["section1"]["key1"], "测试")
