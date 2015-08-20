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

from st2common import operators
from st2common.util import date as date_utils


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
        self.assertTrue(op('', ''), 'Failed equals.')

    def test_equals_fail(self):
        op = operators.get_operator('equals')
        self.assertFalse(op('1', '2'), 'Passed equals.')

    def test_nequals(self):
        op = operators.get_operator('nequals')
        self.assertTrue(op('foo', 'bar'))
        self.assertTrue(op('foo', 'foo1'))
        self.assertTrue(op('foo', 'FOO'))
        self.assertTrue(op('True', True))
        self.assertTrue(op('None', None))

        self.assertFalse(op('True', 'True'))
        self.assertFalse(op(None, None))

    def test_iequals(self):
        op = operators.get_operator('iequals')
        self.assertTrue(op('ABC', 'ABC'), 'Failed iequals.')
        self.assertTrue(op('ABC', 'abc'), 'Failed iequals.')
        self.assertTrue(op('AbC', 'aBc'), 'Failed iequals.')

    def test_iequals_fail(self):
        op = operators.get_operator('iequals')
        self.assertFalse(op('ABC', 'BCA'), 'Failed iequals.')

    def test_contains(self):
        op = operators.get_operator('contains')
        self.assertTrue(op('hasystack needle haystack', 'needle'))
        self.assertTrue(op('needle', 'needle'))
        self.assertTrue(op('needlehaystack', 'needle'))
        self.assertTrue(op('needle haystack', 'needle'))
        self.assertTrue(op('haystackneedle', 'needle'))
        self.assertTrue(op('haystack needle', 'needle'))

    def test_contains_fail(self):
        op = operators.get_operator('contains')
        self.assertFalse(op('hasystack needl haystack', 'needle'))
        self.assertFalse(op('needla', 'needle'))

    def test_icontains(self):
        op = operators.get_operator('icontains')
        self.assertTrue(op('hasystack nEEdle haystack', 'needle'))
        self.assertTrue(op('neeDle', 'NeedlE'))
        self.assertTrue(op('needlehaystack', 'needle'))
        self.assertTrue(op('NEEDLE haystack', 'NEEDLE'))
        self.assertTrue(op('haystackNEEDLE', 'needle'))
        self.assertTrue(op('haystack needle', 'NEEDLE'))

    def test_icontains_fail(self):
        op = operators.get_operator('icontains')
        self.assertFalse(op('hasystack needl haystack', 'needle'))
        self.assertFalse(op('needla', 'needle'))

    def test_ncontains(self):
        op = operators.get_operator('ncontains')
        self.assertTrue(op('hasystack needle haystack', 'foo'))
        self.assertTrue(op('needle', 'foo'))
        self.assertTrue(op('needlehaystack', 'needlex'))
        self.assertTrue(op('needle haystack', 'needlex'))
        self.assertTrue(op('haystackneedle', 'needlex'))
        self.assertTrue(op('haystack needle', 'needlex'))

    def test_ncontains_fail(self):
        op = operators.get_operator('ncontains')
        self.assertFalse(op('hasystack needle haystack', 'needle'))
        self.assertFalse(op('needla', 'needla'))

    def test_incontains(self):
        op = operators.get_operator('incontains')
        self.assertTrue(op('hasystack needle haystack', 'FOO'))
        self.assertTrue(op('needle', 'FOO'))
        self.assertTrue(op('needlehaystack', 'needlex'))
        self.assertTrue(op('needle haystack', 'needlex'))
        self.assertTrue(op('haystackneedle', 'needlex'))
        self.assertTrue(op('haystack needle', 'needlex'))

    def test_incontains_fail(self):
        op = operators.get_operator('incontains')
        self.assertFalse(op('hasystack needle haystack', 'nEeDle'))
        self.assertFalse(op('needlA', 'needlA'))

    def test_startswith(self):
        op = operators.get_operator('startswith')
        self.assertTrue(op('hasystack needle haystack', 'hasystack'))
        self.assertTrue(op('a hasystack needle haystack', 'a '))

    def test_startswith_fail(self):
        op = operators.get_operator('startswith')
        self.assertFalse(op('hasystack needle haystack', 'needle'))
        self.assertFalse(op('a hasystack needle haystack', 'haystack'))

    def test_istartswith(self):
        op = operators.get_operator('istartswith')
        self.assertTrue(op('haystack needle haystack', 'HAYstack'))
        self.assertTrue(op('HAYSTACK needle haystack', 'haystack'))

    def test_istartswith_fail(self):
        op = operators.get_operator('istartswith')
        self.assertFalse(op('hasystack needle haystack', 'NEEDLE'))
        self.assertFalse(op('a hasystack needle haystack', 'haystack'))

    def test_endswith(self):
        op = operators.get_operator('endswith')
        self.assertTrue(op('hasystack needle haystackend', 'haystackend'))
        self.assertTrue(op('a hasystack needle haystack b', 'b'))

    def test_endswith_fail(self):
        op = operators.get_operator('endswith')
        self.assertFalse(op('hasystack needle haystackend', 'haystack'))
        self.assertFalse(op('a hasystack needle haystack', 'a'))

    def test_iendswith(self):
        op = operators.get_operator('iendswith')
        self.assertTrue(op('haystack needle haystackEND', 'HAYstackend'))
        self.assertTrue(op('HAYSTACK needle haystackend', 'haystackEND'))

    def test_iendswith_fail(self):
        op = operators.get_operator('iendswith')
        self.assertFalse(op('hasystack needle haystack', 'NEEDLE'))
        self.assertFalse(op('a hasystack needle haystack', 'a '))

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
        self.assertTrue(op(date_utils.get_datetime_utc_now().isoformat(), 10),
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
        self.assertFalse(op(date_utils.get_datetime_utc_now().isoformat(), 10),
                         'Passed test_timediff_gt.')

    def test_exists(self):
        op = operators.get_operator('exists')
        self.assertTrue(op(False, None), 'Should return True')
        self.assertTrue(op(1, None), 'Should return True')
        self.assertTrue(op('foo', None), 'Should return True')
        self.assertFalse(op(None, None), 'Should return False')

    def test_nexists(self):
        op = operators.get_operator('nexists')
        self.assertFalse(op(False, None), 'Should return False')
        self.assertFalse(op(1, None), 'Should return False')
        self.assertFalse(op('foo', None), 'Should return False')
        self.assertTrue(op(None, None), 'Should return True')
