import datetime
import unittest2

from st2reactor.rules import operators


class OperatorTest(unittest2.TestCase):

    def test_matchregex(self):
        op = operators.get_operator('matchregex')
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
