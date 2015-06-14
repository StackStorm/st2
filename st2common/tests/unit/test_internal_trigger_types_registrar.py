# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the 'License'); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    import simplejson as json
except ImportError:
    import json

import mock
import requests

from st2common.services.access import delete_token
from st2common.triggers import InternalTriggerTypesRegistrar
from st2common.util import date as date_utils

from st2tests.base import (DbTestCase, FakeResponse)

from st2tests import config as tests_config
tests_config.parse_args()

FAKE_TRIGGER = {
    'name': 'foo',
    'pack': 'bar',
    'parameters': {}
}


class InternalTriggerTypesTests(DbTestCase):

    def test_token_successfully_obtained(self):
        time_now = date_utils.get_datetime_utc_now()
        registrar = InternalTriggerTypesRegistrar()
        self.assertTrue(registrar._auth_creds is not None)
        # TTL is at least 10 mins
        self.assertTrue((registrar._auth_creds.expiry - time_now).seconds > 10 * 60)
        delete_token(registrar._auth_creds.token)

    def test_get_trigger_type_url(self):
        registrar = InternalTriggerTypesRegistrar()
        url = registrar._get_trigger_type_url('foo.bar')
        self.assertEqual(url, 'http://localhost:9101/v1/triggertypes/foo.bar')
        delete_token(registrar._auth_creds.token)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=FakeResponse(json.dumps(FAKE_TRIGGER), 200, 'OK')))
    def test_is_triger_type_exists_happy_case(self):
        registrar = InternalTriggerTypesRegistrar()
        is_exists = registrar._is_triggertype_exists('bar.foo')
        self.assertEqual(is_exists, True)
        delete_token(registrar._auth_creds.token)

    @mock.patch.object(
        requests, 'get',
        mock.MagicMock(return_value=FakeResponse(json.dumps('trigger not found'), 404,
                                                 'NOT FOUND')))
    def test_is_triger_type_exists_sad_case(self):
        registrar = InternalTriggerTypesRegistrar()
        is_exists = registrar._is_triggertype_exists('bar.foo')
        self.assertEqual(is_exists, False)
        delete_token(registrar._auth_creds.token)
