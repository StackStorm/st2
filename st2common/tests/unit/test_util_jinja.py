# -*- coding: utf-8 -*-
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

import unittest2

from st2common.util import jinja as jinja_utils


class JinjaUtilsRenderTestCase(unittest2.TestCase):

    def test_render_values(self):
        actual = jinja_utils.render_values(
            mapping={'k1': '{{a}}', 'k2': '{{b}}'},
            context={'a': 'v1', 'b': 'v2'})
        expected = {'k2': 'v2', 'k1': 'v1'}
        self.assertEqual(actual, expected)

    def test_render_values_skip_missing(self):
        actual = jinja_utils.render_values(
            mapping={'k1': '{{a}}', 'k2': '{{b}}', 'k3': '{{c}}'},
            context={'a': 'v1', 'b': 'v2'},
            allow_undefined=True)
        expected = {'k2': 'v2', 'k1': 'v1', 'k3': ''}
        self.assertEqual(actual, expected)

    def test_render_values_ascii_and_unicode_values(self):
        mapping = {
            u'k_ascii': '{{a}}',
            u'k_unicode': '{{b}}',
            u'k_ascii_unicode': '{{c}}'}
        context = {
            'a': u'some ascii value',
            'b': u'٩(̾●̮̮̃̾•̃̾)۶ ٩(̾●̮̮̃̾•̃̾)۶ ćšž',
            'c': u'some ascii some ٩(̾●̮̮̃̾•̃̾)۶ ٩(̾●̮̮̃̾•̃̾)۶ '
        }

        expected = {
            'k_ascii': u'some ascii value',
            'k_unicode': u'٩(̾●̮̮̃̾•̃̾)۶ ٩(̾●̮̮̃̾•̃̾)۶ ćšž',
            'k_ascii_unicode': u'some ascii some ٩(̾●̮̮̃̾•̃̾)۶ ٩(̾●̮̮̃̾•̃̾)۶ '
        }

        actual = jinja_utils.render_values(
            mapping=mapping,
            context=context,
            allow_undefined=True)

        self.assertEqual(actual, expected)

    def test_convert_str_to_raw(self):
        jinja_expr = '{{foobar}}'
        expected_raw_block = '{% raw %}{{foobar}}{% endraw %}'
        self.assertEqual(expected_raw_block, jinja_utils.convert_jinja_to_raw_block(jinja_expr))

        jinja_block_expr = '{% for item in items %}foobar{% end for %}'
        expected_raw_block = '{% raw %}{% for item in items %}foobar{% end for %}{% endraw %}'
        self.assertEqual(
            expected_raw_block,
            jinja_utils.convert_jinja_to_raw_block(jinja_block_expr)
        )

    def test_convert_list_to_raw(self):
        jinja_expr = [
            'foobar',
            '{{foo}}',
            '{{bar}}',
            '{% for item in items %}foobar{% end for %}',
            {'foobar': '{{foobar}}'}
        ]

        expected_raw_block = [
            'foobar',
            '{% raw %}{{foo}}{% endraw %}',
            '{% raw %}{{bar}}{% endraw %}',
            '{% raw %}{% for item in items %}foobar{% end for %}{% endraw %}',
            {'foobar': '{% raw %}{{foobar}}{% endraw %}'}
        ]

        self.assertListEqual(expected_raw_block, jinja_utils.convert_jinja_to_raw_block(jinja_expr))

    def test_convert_dict_to_raw(self):
        jinja_expr = {
            'var1': 'foobar',
            'var2': ['{{foo}}', '{{bar}}'],
            'var3': {'foobar': '{{foobar}}'},
            'var4': {'foobar': '{% for item in items %}foobar{% end for %}'}
        }

        expected_raw_block = {
            'var1': 'foobar',
            'var2': [
                '{% raw %}{{foo}}{% endraw %}',
                '{% raw %}{{bar}}{% endraw %}'
            ],
            'var3': {
                'foobar': '{% raw %}{{foobar}}{% endraw %}'
            },
            'var4': {
                'foobar': '{% raw %}{% for item in items %}foobar{% end for %}{% endraw %}'
            }
        }

        self.assertDictEqual(expected_raw_block, jinja_utils.convert_jinja_to_raw_block(jinja_expr))
