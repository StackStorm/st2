import datetime

import unittest

from st2common.util import isotime


class TestTimeUtil(unittest.TestCase):

    def test_add_utc_tz_info(self):
        dt = datetime.datetime.utcnow()
        self.assertIsNone(dt.tzinfo)
        dt = isotime.add_utc_tz(dt)
        self.assertIsNotNone(dt.tzinfo)
        self.assertEqual(dt.tzinfo.tzname(None), 'UTC')

    def test_validate(self):
        self.assertTrue(isotime.validate('2000-01-01 12:00:00Z'))
        self.assertTrue(isotime.validate('2000-01-01 12:00:00+00'))
        self.assertTrue(isotime.validate('2000-01-01 12:00:00+0000'))
        self.assertTrue(isotime.validate('2000-01-01 12:00:00+00:00'))
        self.assertTrue(isotime.validate('2000-01-01 12:00:00.000000Z'))
        self.assertTrue(isotime.validate('2000-01-01 12:00:00.000000+00'))
        self.assertTrue(isotime.validate('2000-01-01 12:00:00.000000+0000'))
        self.assertTrue(isotime.validate('2000-01-01 12:00:00.000000+00:00'))
        self.assertTrue(isotime.validate('2000-01-01T12:00:00Z'))
        self.assertTrue(isotime.validate('2000-01-01T12:00:00.000000Z'))
        self.assertTrue(isotime.validate('2000-01-01T12:00:00+00:00'))
        self.assertTrue(isotime.validate('2000-01-01T12:00:00.000000+00:00'))
        self.assertFalse(isotime.validate('2000-01-01', raise_exception=False))
        self.assertFalse(isotime.validate('2000-01-01T12:00:00', raise_exception=False))
        self.assertFalse(isotime.validate('2000-01-01T12:00:00+00:00Z', raise_exception=False))
        self.assertFalse(isotime.validate('2000-01-01T12:00:00.000000', raise_exception=False))
        self.assertFalse(isotime.validate('Epic!', raise_exception=False))
        self.assertFalse(isotime.validate(object(), raise_exception=False))
        self.assertRaises(ValueError, isotime.validate, 'Epic!', True)

    def test_parse(self):
        dt = isotime.add_utc_tz(datetime.datetime(2000, 1, 1, 12))
        self.assertEqual(isotime.parse('2000-01-01 12:00:00Z'), dt)
        self.assertEqual(isotime.parse('2000-01-01 12:00:00+00'), dt)
        self.assertEqual(isotime.parse('2000-01-01 12:00:00+0000'), dt)
        self.assertEqual(isotime.parse('2000-01-01 12:00:00+00:00'), dt)
        self.assertEqual(isotime.parse('2000-01-01 12:00:00.000000Z'), dt)
        self.assertEqual(isotime.parse('2000-01-01 12:00:00.000000+00'), dt)
        self.assertEqual(isotime.parse('2000-01-01 12:00:00.000000+0000'), dt)
        self.assertEqual(isotime.parse('2000-01-01 12:00:00.000000+00:00'), dt)
        self.assertEqual(isotime.parse('2000-01-01T12:00:00Z'), dt)
        self.assertEqual(isotime.parse('2000-01-01T12:00:00+00:00'), dt)
        self.assertEqual(isotime.parse('2000-01-01T12:00:00.000000Z'), dt)
        self.assertEqual(isotime.parse('2000-01-01T12:00:00.000000+00:00'), dt)

    def test_format(self):
        dt = isotime.add_utc_tz(datetime.datetime(2000, 1, 1, 12))
        self.assertEqual(
            isotime.format(dt, usec=True, offset=True), '2000-01-01T12:00:00.000000+00:00')
        self.assertEqual(
            isotime.format(dt, usec=True, offset=False), '2000-01-01T12:00:00.000000Z')
        self.assertEqual(isotime.format(dt, usec=False, offset=True), '2000-01-01T12:00:00+00:00')
        self.assertEqual(isotime.format(dt, usec=False, offset=False), '2000-01-01T12:00:00Z')

    def test_format_tz_naive(self):
        dt1 = datetime.datetime.utcnow()
        dt2 = isotime.parse(isotime.format(dt1, usec=True))
        self.assertEqual(dt2, isotime.add_utc_tz(dt1))

    def test_format_tz_aware(self):
        dt1 = isotime.add_utc_tz(datetime.datetime.utcnow())
        dt2 = isotime.parse(isotime.format(dt1, usec=True))
        self.assertEqual(dt2, dt1)

    def test_format_sec_truncated(self):
        dt1 = isotime.add_utc_tz(datetime.datetime.utcnow())
        dt2 = isotime.parse(isotime.format(dt1, usec=False))
        dt3 = datetime.datetime(dt1.year, dt1.month, dt1.day, dt1.hour, dt1.minute, dt1.second)
        self.assertLess(dt2, dt1)
        self.assertEqual(dt2, isotime.add_utc_tz(dt3))
