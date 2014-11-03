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

import datetime
import unittest2

from st2common import operators


class OperatorTest(unittest2.TestCase):

    def test_matchregex(self):
        op = operators.get_operator('matchregex')
        self.assertTrue(op('v1', 'v1$'), 'Failed matchregex.')

    def test_matchregex_case_variants(self):
        op = operators.get_operator('MATCHREGEX')
        self.assertTrue(op('v1', 'v1$'), 'Failed matchregex.')
        op = operators.get_operator('MATCHregex')
        self.assertTrue(op('v1', 'v1$'), 'Failed matchregex.')

    def test_matchregex_fail(self):
        op = operators.get_operator('matchregex')
        self.assertFalse(op('v1_foo', 'v1$'), 'Passed matchregex.')

    def test_equals_numeric(self):
        op = operators.get_operator('equals')
        self.assertTrue(op(1, 1), 'Failed equals.')

    def test_equals_string(self):
        op = operators.get_operator('equals')
        self.assertTrue(op('1', '1'), 'Failed equals.')

    def test_equals_fail(self):
        op = operators.get_operator('equals')
        self.assertFalse(op('1', '2'), 'Passed equals.')

    def test_lt(self):
        op = operators.get_operator('lessthan')
        self.assertTrue(op(1, 2), 'Failed lessthan.')

    def test_lt_char(self):
        op = operators.get_operator('lessthan')
        self.assertTrue(op('a', 'b'), 'Failed lessthan.')

    def test_lt_fail(self):
        op = operators.get_operator('lessthan')
        self.assertFalse(op(1, 1), 'Passed lessthan.')

    def test_gt(self):
        op = operators.get_operator('greaterthan')
        self.assertTrue(op(2, 1), 'Failed greaterthan.')

    def test_gt_str(self):
        op = operators.get_operator('lessthan')
        self.assertTrue(op('aba', 'bcb'), 'Failed greaterthan.')

    def test_gt_fail(self):
        op = operators.get_operator('greaterthan')
        self.assertFalse(op(2, 3), 'Passed greaterthan.')

    def test_timediff_lt(self):
        op = operators.get_operator('timediff_lt')
        self.assertTrue(op(datetime.datetime.utcnow().isoformat(), 10),
                        'Failed test_timediff_lt.')

    def test_timediff_lt_fail(self):
        op = operators.get_operator('timediff_lt')
        self.assertFalse(op('2014-07-01T00:01:01.000000', 10),
                        'Passed test_timediff_lt.')

    def test_timediff_gt(self):
        op = operators.get_operator('timediff_gt')
        self.assertTrue(op('2014-07-01T00:01:01.000000', 1),
                        'Failed test_timediff_gt.')

    def test_timediff_gt_fail(self):
        op = operators.get_operator('timediff_gt')
        self.assertFalse(op(datetime.datetime.utcnow().isoformat(), 10),
                         'Passed test_timediff_gt.')
