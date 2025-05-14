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

from st2common.util.misc import rstrip_last_char
from st2common.util.misc import strip_shell_chars
from st2common.util.misc import lowercase_value
from st2common.util.misc import sanitize_output
from st2common.util.deep_copy import fast_deepcopy_dict

__all__ = ["MiscUtilTestCase"]


class MiscUtilTestCase(unittest.TestCase):
    def test_rstrip_last_char(self):
        self.assertEqual(rstrip_last_char(None, "\n"), None)
        self.assertEqual(rstrip_last_char("stuff", None), "stuff")
        self.assertEqual(rstrip_last_char("", "\n"), "")
        self.assertEqual(rstrip_last_char("foo", "\n"), "foo")
        self.assertEqual(rstrip_last_char("foo\n", "\n"), "foo")
        self.assertEqual(rstrip_last_char("foo\n\n", "\n"), "foo\n")
        self.assertEqual(rstrip_last_char("foo\r", "\r"), "foo")
        self.assertEqual(rstrip_last_char("foo\r\r", "\r"), "foo\r")
        self.assertEqual(rstrip_last_char("foo\r\n", "\r\n"), "foo")
        self.assertEqual(rstrip_last_char("foo\r\r\n", "\r\n"), "foo\r")
        self.assertEqual(rstrip_last_char("foo\n\r", "\r\n"), "foo\n\r")

    def test_strip_shell_chars(self):
        self.assertEqual(strip_shell_chars(None), None)
        self.assertEqual(strip_shell_chars("foo"), "foo")
        self.assertEqual(strip_shell_chars("foo\r"), "foo")
        self.assertEqual(strip_shell_chars("fo\ro\r"), "fo\ro")
        self.assertEqual(strip_shell_chars("foo\n"), "foo")
        self.assertEqual(strip_shell_chars("fo\no\n"), "fo\no")
        self.assertEqual(strip_shell_chars("foo\r\n"), "foo")
        self.assertEqual(strip_shell_chars("fo\no\r\n"), "fo\no")
        self.assertEqual(strip_shell_chars("foo\r\n\r\n"), "foo\r\n")

    def test_lowercase_value(self):
        value = "TEST"
        expected_value = "test"
        self.assertEqual(expected_value, lowercase_value(value=value))

        value = ["testA", "TESTb", "TESTC"]
        expected_value = ["testa", "testb", "testc"]
        self.assertEqual(expected_value, lowercase_value(value=value))

        value = {"testA": "testB", "testC": "TESTD", "TESTE": "TESTE"}
        expected_value = {"testa": "testb", "testc": "testd", "teste": "teste"}
        self.assertEqual(expected_value, lowercase_value(value=value))

    def test_fast_deepcopy_dict_success(self):
        class Foo(object):
            a = 1
            b = 2
            c = 3
            d = [1, 2, 3]

        obj = Foo()

        values = [
            "a",
            "٩(̾●̮̮̃̾•̃̾)۶",
            1,
            [1, 2, "3", "b"],
            {"a": 1, "b": "3333", "c": "d"},
        ]
        expected_values = [
            "a",
            "٩(̾●̮̮̃̾•̃̾)۶",
            1,
            [1, 2, "3", "b"],
            {"a": 1, "b": "3333", "c": "d"},
        ]

        for value, expected_value in zip(values, expected_values):
            result = fast_deepcopy_dict(value)
            self.assertEqual(result, value)
            self.assertEqual(result, expected_value)

        # Non-simple type, should fall back to copy.deepcopy()
        value = {"a": 1, "b": [1, 2, 3], "c": obj}
        expected_value = {"a": 1, "b": [1, 2, 3]}

        result = fast_deepcopy_dict(value)
        result_c = result.pop("c")
        self.assertEqual(result, expected_value)
        self.assertEqual(result_c.a, 1)
        self.assertEqual(result_c.b, 2)
        self.assertEqual(result_c.c, 3)
        self.assertEqual(result_c.d, [1, 2, 3])

        # fall_back_to_deepcopy=False
        self.assertRaises(
            TypeError, fast_deepcopy_dict, value, fall_back_to_deepcopy=False
        )

    def test_sanitize_output_use_pyt_false(self):
        # pty is not used, \r\n shouldn't be replaced with \n
        input_strs = [
            "foo",
            "foo\n",
            "foo\r\n",
            "foo\nbar\nbaz\n",
            "foo\r\nbar\r\nbaz\r\n",
        ]
        expected = [
            "foo",
            "foo",
            "foo",
            "foo\nbar\nbaz",
            "foo\r\nbar\r\nbaz",
        ]

        for input_str, expected_output in zip(input_strs, expected):
            output = sanitize_output(input_str, uses_pty=False)
            self.assertEqual(expected_output, output)

    def test_sanitize_output_use_pyt_true(self):
        # pty is used, \r\n should be replaced with \n
        input_strs = [
            "foo",
            "foo\n",
            "foo\r\n",
            "foo\nbar\nbaz\n",
            "foo\r\nbar\r\nbaz\r\n",
        ]
        expected = [
            "foo",
            "foo",
            "foo",
            "foo\nbar\nbaz",
            "foo\nbar\nbaz",
        ]

        for input_str, expected_output in zip(input_strs, expected):
            output = sanitize_output(input_str, uses_pty=True)
            self.assertEqual(expected_output, output)
