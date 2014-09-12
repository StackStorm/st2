import uuid
import datetime
import random
import string

import mock
import pecan
import jsonschema
from oslo.config import cfg

from tests.base import FunctionalTest
from st2common.models.db.access import UserDB
from st2common.models.api.access import TokenAPI
from st2common.persistence.access import User


USERNAME = ''.join(random.choice(string.lowercase) for i in range(10))


class TestTokenController(FunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(TestTokenController, cls).setUpClass()
        type(pecan.request).remote_user = mock.PropertyMock(return_value=USERNAME)

    def test_token_model(self):
        tk1 = TokenAPI(user='stanley', token=uuid.uuid4().hex, expiry=datetime.datetime.now())
        tk2 = TokenAPI.from_model(TokenAPI.to_model(tk1))
        self.assertEqual(tk1.__dict__, tk2.__dict__)

    def test_token_model_null_token(self):
        self.assertRaises(jsonschema.exceptions.ValidationError, TokenAPI,
                          user='stanley', token=None, expiry=datetime.datetime.now())

    def test_token_model_null_user(self):
        self.assertRaises(jsonschema.exceptions.ValidationError, TokenAPI,
                          user=None, token=uuid.uuid4().hex, expiry=datetime.datetime.now())

    def test_token_model_null_expiry(self):
        self.assertRaises(ValueError, TokenAPI,
                          user='stanley', token=uuid.uuid4().hex, expiry=None)

    def _test_token_post(self):
        ttl = cfg.CONF.auth.token_ttl
        timestamp = datetime.datetime.now()
        response = self.app.post_json('/tokens', {}, expect_errors=False)
        expected_expiry = datetime.datetime.now() + datetime.timedelta(seconds=ttl)
        self.assertEqual(response.status_int, 201)
        self.assertIsNotNone(response.json['token'])
        self.assertEqual(response.json['user'], USERNAME)
        regexp_datetime = r'^\d{4}-\d{2}-\d{2}[ ]\d{2}:\d{2}:\d{2}.\d{6}$'
        self.assertRegexpMatches(response.json['expiry'], regexp_datetime)
        actual_expiry = datetime.datetime.strptime(response.json['expiry'], '%Y-%m-%d %H:%M:%S.%f')
        self.assertLess(timestamp, actual_expiry)
        self.assertLess(actual_expiry, expected_expiry)

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        User, 'add_or_update',
        mock.Mock(return_value=UserDB(user=USERNAME, active=True)))
    def test_token_post_new_user(self):
        self._test_token_post()

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name=USERNAME, active=True)))
    def test_token_post_existing_user(self):
        self._test_token_post()

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name=USERNAME, active=False)))
    def test_token_post_inactive_user(self):
        response = self.app.post_json('/tokens', {}, expect_errors=True)
        self.assertEqual(response.status_int, 401)

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name=USERNAME, active=True)))
    def test_token_post_set_ttl(self):
        timestamp = datetime.datetime.now()
        response = self.app.post_json('/tokens', {'ttl': 60}, expect_errors=False)
        expected_expiry = datetime.datetime.now() + datetime.timedelta(seconds=60)
        self.assertEqual(response.status_int, 201)
        actual_expiry = datetime.datetime.strptime(response.json['expiry'], '%Y-%m-%d %H:%M:%S.%f')
        self.assertLess(timestamp, actual_expiry)
        self.assertLess(actual_expiry, expected_expiry)

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name=USERNAME, active=True)))
    def test_token_post_auth_disabled_set_ttl_over_policy(self):
        ttl = cfg.CONF.auth.token_ttl
        timestamp = datetime.datetime.now()
        response = self.app.post_json('/tokens', {'ttl': ttl + 60}, expect_errors=False)
        expected_expiry = datetime.datetime.now() + datetime.timedelta(seconds=ttl)
        self.assertLess(expected_expiry, timestamp + datetime.timedelta(seconds=ttl + 60))
        self.assertEqual(response.status_int, 201)
        actual_expiry = datetime.datetime.strptime(response.json['expiry'], '%Y-%m-%d %H:%M:%S.%f')
        self.assertLess(timestamp, actual_expiry)
        self.assertLess(actual_expiry, expected_expiry)

    @mock.patch.object(
        User, 'get_by_name',
        mock.MagicMock(return_value=UserDB(name=USERNAME, active=True)))
    def test_token_post_auth_disabled_bad_ttl(self):
        response = self.app.post_json('/tokens', {'ttl': -1}, expect_errors=True)
        self.assertEqual(response.status_int, 400)
        response = self.app.post_json('/tokens', {'ttl': 0}, expect_errors=True)
        self.assertEqual(response.status_int, 400)
