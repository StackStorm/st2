import datetime
import tests.config

from oslo.config import cfg
from st2tests.base import DbTestCase
from st2common.exceptions.access import TokenNotFoundError
from st2common.persistence.access import Token
from st2common.services import access


class AccessServiceTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(AccessServiceTest, cls).setUpClass()
        tests.config.parse_args()

    def test_create_token(self):
        token = access.create_token('manas')
        self.assertTrue(token is not None)
        self.assertTrue(token.token is not None)
        self.assertEqual(token.user, 'manas')

    def test_create_token_fail(self):
        try:
            access.create_token(None)
            self.assertTrue(False, 'Create succeeded was expected to fail.')
        except ValueError:
            self.assertTrue(True)

    def test_delete_token(self):
        token = access.create_token('manas')
        access.delete_token(token.token)
        try:
            token = Token.get(token.token)
            self.assertTrue(False, 'Delete failed was expected to pass.')
        except TokenNotFoundError:
            self.assertTrue(True)

    def test_create_token_ttl_ok(self):
        ttl = 10
        token = access.create_token('manas', 10)
        self.assertTrue(token is not None)
        self.assertTrue(token.token is not None)
        self.assertEqual(token.user, 'manas')
        expected_expiry = datetime.datetime.now() + datetime.timedelta(seconds=ttl)
        self.assertLess(token.expiry, expected_expiry)

    def test_create_token_ttl_capped(self):
        ttl = cfg.CONF.auth.token_ttl + 10
        expected_expiry = datetime.datetime.now() + datetime.timedelta(seconds=ttl)
        token = access.create_token('manas', 10)
        self.assertTrue(token is not None)
        self.assertTrue(token.token is not None)
        self.assertEqual(token.user, 'manas')
        self.assertLess(token.expiry, expected_expiry)
