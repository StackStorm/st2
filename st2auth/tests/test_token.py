import uuid
import datetime
import random
import string

import mock
import pecan
from oslo.config import cfg

from tests.base import FunctionalTest
from st2common.util import isotime
from st2common.models.db.access import UserDB, TokenDB
from st2common.models.api.access import TokenAPI
from st2common.persistence.access import User, Token


USERNAME = ''.join(random.choice(string.lowercase) for i in range(10))


class TestTokenController(FunctionalTest):

    def setUp(self):
        super(TestTokenController, self).setUp()
        type(pecan.request).remote_user = mock.PropertyMock(return_value=USERNAME)

    def test_token_model(self):
        dt = isotime.add_utc_tz(datetime.datetime.utcnow())
        tk1 = TokenAPI(user='stanley', token=uuid.uuid4().hex,
                       expiry=isotime.format(dt, offset=False))
        tkdb1 = TokenAPI.to_model(tk1)
        self.assertIsNotNone(tkdb1)
        self.assertIsInstance(tkdb1, TokenDB)
        self.assertEqual(tkdb1.user, tk1.user)
        self.assertEqual(tkdb1.token, tk1.token)
        self.assertEqual(tkdb1.expiry, isotime.parse(tk1.expiry))
        tkdb2 = Token.add_or_update(tkdb1)
        self.assertEqual(tkdb1, tkdb2)
        self.assertIsNotNone(tkdb2.id)
        tk2 = TokenAPI.from_model(tkdb2)
        self.assertEqual(tk2.user, tk1.user)
        self.assertEqual(tk2.token, tk1.token)
        self.assertEqual(tk2.expiry, tk1.expiry)

    def test_token_model_null_token(self):
        dt = isotime.add_utc_tz(datetime.datetime.utcnow())
        tk = TokenAPI(user='stanley', token=None, expiry=isotime.format(dt))
        self.assertRaises(ValueError, Token.add_or_update, TokenAPI.to_model(tk))

    def test_token_model_null_user(self):
        dt = isotime.add_utc_tz(datetime.datetime.utcnow())
        tk = TokenAPI(user=None, token=uuid.uuid4().hex, expiry=isotime.format(dt))
        self.assertRaises(ValueError, Token.add_or_update, TokenAPI.to_model(tk))

    def test_token_model_null_expiry(self):
        tk = TokenAPI(user='stanley', token=uuid.uuid4().hex, expiry=None)
        self.assertRaises(ValueError, Token.add_or_update, TokenAPI.to_model(tk))

    def _test_token_post(self):
        ttl = cfg.CONF.auth.token_ttl
        timestamp = isotime.add_utc_tz(datetime.datetime.utcnow())
        response = self.app.post_json('/tokens', {}, expect_errors=False)
        expected_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=ttl)
        expected_expiry = isotime.add_utc_tz(expected_expiry)
        self.assertEqual(response.status_int, 201)
        self.assertIsNotNone(response.json['token'])
        self.assertEqual(response.json['user'], USERNAME)
        actual_expiry = isotime.parse(response.json['expiry'])
        self.assertLess(timestamp, actual_expiry)
        self.assertLess(actual_expiry, expected_expiry)

    def test_token_post_unauthorized(self):
        type(pecan.request).remote_user = None
        response = self.app.post_json('/tokens', {}, expect_errors=True)
        self.assertEqual(response.status_int, 401)

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(side_effect=Exception()))
    @mock.patch.object(
        User, 'add_or_update',
        mock.Mock(return_value=UserDB(user=USERNAME)))
    def test_token_post_new_user(self):
        self._test_token_post()

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name=USERNAME)))
    def test_token_post_existing_user(self):
        self._test_token_post()

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name=USERNAME)))
    def test_token_post_set_ttl(self):
        timestamp = isotime.add_utc_tz(datetime.datetime.utcnow())
        response = self.app.post_json('/tokens', {'ttl': 60}, expect_errors=False)
        expected_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=60)
        expected_expiry = isotime.add_utc_tz(expected_expiry)
        self.assertEqual(response.status_int, 201)
        actual_expiry = isotime.parse(response.json['expiry'])
        self.assertLess(timestamp, actual_expiry)
        self.assertLess(actual_expiry, expected_expiry)

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name=USERNAME)))
    def test_token_post_set_ttl_over_policy(self):
        ttl = cfg.CONF.auth.token_ttl
        timestamp = isotime.add_utc_tz(datetime.datetime.utcnow())
        response = self.app.post_json('/tokens', {'ttl': ttl + 60}, expect_errors=False)
        expected_expiry = datetime.datetime.utcnow() + datetime.timedelta(seconds=ttl)
        expected_expiry = isotime.add_utc_tz(expected_expiry)
        self.assertLess(expected_expiry, timestamp + datetime.timedelta(seconds=ttl + 60))
        self.assertEqual(response.status_int, 201)
        actual_expiry = isotime.parse(response.json['expiry'])
        self.assertLess(timestamp, actual_expiry)
        self.assertLess(actual_expiry, expected_expiry)

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name=USERNAME)))
    def test_token_post_set_bad_ttl(self):
        response = self.app.post_json('/tokens', {'ttl': -1}, expect_errors=True)
        self.assertEqual(response.status_int, 400)
        response = self.app.post_json('/tokens', {'ttl': 0}, expect_errors=True)
        self.assertEqual(response.status_int, 400)
