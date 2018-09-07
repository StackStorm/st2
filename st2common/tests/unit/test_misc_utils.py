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

from __future__ import absolute_import

import json
import copy
import string
import random
from timeit import default_timer as timer

import unittest2

from st2common.util.misc import rstrip_last_char
from st2common.util.misc import strip_shell_chars
from st2common.util.misc import lowercase_value
from st2common.util.ujson import fast_deepcopy

__all__ = [
    'MiscUtilTestCase'
]


class MiscUtilTestCase(unittest2.TestCase):
    def test_rstrip_last_char(self):
        self.assertEqual(rstrip_last_char(None, '\n'), None)
        self.assertEqual(rstrip_last_char('stuff', None), 'stuff')
        self.assertEqual(rstrip_last_char('', '\n'), '')
        self.assertEqual(rstrip_last_char('foo', '\n'), 'foo')
        self.assertEqual(rstrip_last_char('foo\n', '\n'), 'foo')
        self.assertEqual(rstrip_last_char('foo\n\n', '\n'), 'foo\n')
        self.assertEqual(rstrip_last_char('foo\r', '\r'), 'foo')
        self.assertEqual(rstrip_last_char('foo\r\r', '\r'), 'foo\r')
        self.assertEqual(rstrip_last_char('foo\r\n', '\r\n'), 'foo')
        self.assertEqual(rstrip_last_char('foo\r\r\n', '\r\n'), 'foo\r')
        self.assertEqual(rstrip_last_char('foo\n\r', '\r\n'), 'foo\n\r')

    def test_strip_shell_chars(self):
        self.assertEqual(strip_shell_chars(None), None)
        self.assertEqual(strip_shell_chars('foo'), 'foo')
        self.assertEqual(strip_shell_chars('foo\r'), 'foo')
        self.assertEqual(strip_shell_chars('fo\ro\r'), 'fo\ro')
        self.assertEqual(strip_shell_chars('foo\n'), 'foo')
        self.assertEqual(strip_shell_chars('fo\no\n'), 'fo\no')
        self.assertEqual(strip_shell_chars('foo\r\n'), 'foo')
        self.assertEqual(strip_shell_chars('fo\no\r\n'), 'fo\no')
        self.assertEqual(strip_shell_chars('foo\r\n\r\n'), 'foo\r\n')

    def test_lowercase_value(self):
        value = 'TEST'
        expected_value = 'test'
        self.assertEqual(expected_value, lowercase_value(value=value))

        value = ['testA', 'TESTb', 'TESTC']
        expected_value = ['testa', 'testb', 'testc']
        self.assertEqual(expected_value, lowercase_value(value=value))

        value = {
            'testA': 'testB',
            'testC': 'TESTD',
            'TESTE': 'TESTE'
        }
        expected_value = {
            'testa': 'testb',
            'testc': 'testd',
            'teste': 'teste'
        }
        self.assertEqual(expected_value, lowercase_value(value=value))

    def test_fast_deepcopy_success(self):
        values = [
            'a',
            u'٩(̾●̮̮̃̾•̃̾)۶',
            1,
            [1, 2, '3', 'b'],
            {'a': 1, 'b': '3333', 'c': 'd'},
        ]
        expected_values = [
            'a',
            u'٩(̾●̮̮̃̾•̃̾)۶',
            1,
            [1, 2, '3', 'b'],
            {'a': 1, 'b': '3333', 'c': 'd'},
        ]

        for value, expected_value in zip(values, expected_values):
            result = fast_deepcopy(value)
            self.assertEqual(result, value)
            self.assertEqual(result, expected_value)

    def test_fast_deepcopy_is_faster_than_copy_deepcopy(self):
        def random_string(N):
            return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(N))

        def random_dict(width=5, height=5, levels=2):
            dct = {}
            lst = [random_string(4) for i in range(width)]
            lst2 = [random.randint(0, 10000) for i in range(width)]
            lst3 = [bool(random.randint(0, 1)) for i in range(width)]
            for j in range(height):
                dct[str(j)] = lst
                dct[str(width + j)] = lst2
                dct[str(2 * width + j)] = lst3

            for i in range(levels):
                new_dct = {}
                for j in range(height):
                    new_dct[str(j)] = dct
                dct = json.loads(json.dumps(new_dct))

            return new_dct

        error_msg = 'fast_deepcopy is not faster than copy.deepcopy'

        # 1. Smaller dict
        data = random_dict(width=10, levels=2, height=2)

        # fast_deepcopy
        start = timer()
        fast_deepcopy(data)
        end = timer()
        duration_1 = (end - start)

        # copy.deepcopy
        start = timer()
        copy.deepcopy(data)
        end = timer()
        duration_2 = (end - start)

        self.assertTrue(duration_1 < duration_2, error_msg)

        # 2. Medium sized dict
        data = random_dict(width=20, levels=3, height=4)

        # fast_deepcopy
        start = timer()
        fast_deepcopy(data)
        end = timer()
        duration_1 = (end - start)

        # copy.deepcopy
        start = timer()
        copy.deepcopy(data)
        end = timer()
        duration_2 = (end - start)

        self.assertTrue(duration_1 < duration_2, error_msg)

        # 3. Larger dict
        data = random_dict(width=30, levels=5, height=4)

        # fast_deepcopy
        start = timer()
        fast_deepcopy(data)
        end = timer()
        duration_1 = (end - start)

        # copy.deepcopy
        start = timer()
        copy.deepcopy(data)
        end = timer()
        duration_2 = (end - start)

        self.assertTrue(duration_1 < duration_2, error_msg)
