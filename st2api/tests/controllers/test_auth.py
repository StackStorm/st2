import uuid
import datetime

import bson
import mock

from tests import AuthMiddlewareTest
from st2common.models.db.access import TokenDB
from st2common.persistence.access import Token
from st2common.exceptions.access import TokenNotFoundError


OBJ_ID = bson.ObjectId()
USER = 'stanley'
TOKEN = uuid.uuid4().hex
FUTURE = datetime.datetime.now() + datetime.timedelta(seconds=300)
PAST = datetime.datetime.now() + datetime.timedelta(seconds=-300)


class TestTokenValidation(AuthMiddlewareTest):

    @mock.patch.object(
        Token, 'get',
        mock.Mock(return_value=TokenDB(id=OBJ_ID, user=USER, token=TOKEN, expiry=FUTURE)))
    def test_token_validation(self):
        response = self.app.get('/actions', headers={'X-Auth-Token': TOKEN}, expect_errors=False)
        self.assertEqual(response.status_int, 200)

    @mock.patch.object(
        Token, 'get',
        mock.Mock(return_value=TokenDB(id=OBJ_ID, user=USER, token=TOKEN, expiry=PAST)))
    def test_token_expired(self):
        response = self.app.get('/actions', headers={'X-Auth-Token': TOKEN}, expect_errors=True)
        self.assertEqual(response.status_int, 401)

    @mock.patch.object(
        Token, 'get', mock.MagicMock(side_effect=TokenNotFoundError()))
    def test_token_not_found(self):
        response = self.app.get('/actions', headers={'X-Auth-Token': TOKEN}, expect_errors=True)
        self.assertEqual(response.status_int, 401)

    def test_token_not_provided(self):
        response = self.app.get('/actions', expect_errors=True)
        self.assertEqual(response.status_int, 401)
