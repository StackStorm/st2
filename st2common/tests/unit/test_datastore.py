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
import os
from datetime import timedelta
from st2common.util.date import get_datetime_utc_now

import mock

from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.services.datastore import BaseDatastoreService
from st2common.services.datastore import SensorDatastoreService
from st2client.models.keyvalue import KeyValuePair

from st2tests import DbTestCase
from st2tests import config

__all__ = ["DatastoreServiceTestCase"]

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
RESOURCES_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../resources"))


class DatastoreServiceTestCase(DbTestCase):
    def setUp(self):
        super(DatastoreServiceTestCase, self).setUp()
        config.parse_args()

        self._datastore_service = BaseDatastoreService(
            logger=mock.Mock(), pack_name="core", class_name="TestSensor"
        )
        self._datastore_service.get_api_client = mock.Mock()

    def test_datastore_operations_list_values(self):
        # Verify prefix filtering
        mock_api_client = mock.Mock()
        mock_api_client.keys.get_all.return_value = []
        self._set_mock_api_client(mock_api_client)

        self._datastore_service.list_values(local=True, prefix=None)
        mock_api_client.keys.get_all.assert_called_with(
            prefix="core.TestSensor:", limit=100, offset=0
        )
        self._datastore_service.list_values(local=True, prefix="ponies")
        mock_api_client.keys.get_all.assert_called_with(
            prefix="core.TestSensor:ponies", limit=100, offset=0
        )

        self._datastore_service.list_values(local=False, prefix=None)
        mock_api_client.keys.get_all.assert_called_with(
            prefix=None, limit=100, offset=0
        )
        self._datastore_service.list_values(local=False, prefix="ponies")
        mock_api_client.keys.get_all.assert_called_with(
            prefix="ponies", limit=100, offset=0
        )

        # No values in the datastore
        mock_api_client = mock.Mock()
        mock_api_client.keys.get_all.return_value = []
        self._set_mock_api_client(mock_api_client)

        values = self._datastore_service.list_values(local=True)
        self.assertEqual(values, [])
        values = self._datastore_service.list_values(local=False)
        self.assertEqual(values, [])

        # Values in the datastore
        kvp1 = KeyValuePair()
        kvp1.name = "test1"
        kvp1.value = "bar"
        kvp2 = KeyValuePair()
        kvp2.name = "test2"
        kvp2.value = "bar"
        mock_return_value = [kvp1, kvp2]
        mock_api_client.keys.get_all.return_value = mock_return_value
        self._set_mock_api_client(mock_api_client)

        values = self._datastore_service.list_values(local=True)
        self.assertEqual(len(values), 2)
        self.assertEqual(values, mock_return_value)

        # Test limit
        _ = self._datastore_service.list_values(local=True, limit=1)
        mock_api_client.keys.get_all.assert_called_with(
            prefix="core.TestSensor:", limit=1, offset=0
        )

        # Test offset
        _ = self._datastore_service.list_values(local=True, offset=1)
        mock_api_client.keys.get_all.assert_called_with(
            prefix="core.TestSensor:", limit=100, offset=1
        )

    def test_datastore_operations_get_value(self):
        mock_api_client = mock.Mock()
        kvp1 = KeyValuePair()
        kvp1.name = "test1"
        kvp1.value = "bar"
        mock_api_client.keys.get_by_id.return_value = kvp1
        self._set_mock_api_client(mock_api_client)

        value = self._datastore_service.get_value(name="test1", local=False)
        self.assertEqual(value, kvp1.value)

    def test_datastore_operations_set_value(self):
        mock_api_client = mock.Mock()
        mock_api_client.keys.update.return_value = True
        self._set_mock_api_client(mock_api_client)

        value = self._datastore_service.set_value(
            name="test1", value="foo", local=False
        )
        self.assertTrue(value)
        kvp = mock_api_client.keys.update.call_args[1]["instance"]
        self.assertEqual(kvp.value, "foo")
        self.assertEqual(kvp.scope, SYSTEM_SCOPE)

    def test_datastore_operations_delete_value(self):
        mock_api_client = mock.Mock()
        mock_api_client.keys.delete.return_value = True
        self._set_mock_api_client(mock_api_client)

        value = self._datastore_service.delete_value(name="test", local=False)
        self.assertTrue(value)

    def test_datastore_operations_set_encrypted_value(self):
        mock_api_client = mock.Mock()
        mock_api_client.keys.update.return_value = True
        self._set_mock_api_client(mock_api_client)
        value = self._datastore_service.set_value(
            name="test1", value="foo", local=False, encrypt=True
        )
        self.assertTrue(value)
        kvp = mock_api_client.keys.update.call_args[1]["instance"]
        self.assertEqual(kvp.value, "foo")
        self.assertTrue(kvp.secret)
        self.assertEqual(kvp.scope, SYSTEM_SCOPE)

    def test_datastore_unsupported_scope(self):
        self.assertRaises(
            ValueError,
            self._datastore_service.get_value,
            name="test1",
            scope="NOT_SYSTEM",
        )
        self.assertRaises(
            ValueError,
            self._datastore_service.set_value,
            name="test1",
            value="foo",
            scope="NOT_SYSTEM",
        )
        self.assertRaises(
            ValueError,
            self._datastore_service.delete_value,
            name="test1",
            scope="NOT_SYSTEM",
        )

    def test_datastore_get_exception(self):
        mock_api_client = mock.Mock()
        mock_api_client.keys.get_by_id.side_effect = ValueError("Exception test")
        self._set_mock_api_client(mock_api_client)
        value = self._datastore_service.get_value(name="test1")
        self.assertEqual(value, None)

    def test_datastore_delete_exception(self):
        mock_api_client = mock.Mock()
        mock_api_client.keys.delete.side_effect = ValueError("Exception test")
        self._set_mock_api_client(mock_api_client)
        delete_success = self._datastore_service.delete_value(name="test1")
        self.assertEqual(delete_success, False)

    def test_datastore_token_timeout(self):
        datastore_service = SensorDatastoreService(
            logger=mock.Mock(),
            pack_name="core",
            class_name="TestSensor",
            api_username="sensor_service",
        )

        mock_api_client = mock.Mock()
        kvp1 = KeyValuePair()
        kvp1.name = "test1"
        kvp1.value = "bar"
        mock_api_client.keys.get_by_id.return_value = kvp1

        token_expire_time = get_datetime_utc_now() - timedelta(seconds=5)
        datastore_service._client = mock_api_client
        datastore_service._token_expire = token_expire_time

        self._set_mock_api_client(mock_api_client)

        with mock.patch(
            "st2common.services.datastore.Client", return_value=mock_api_client
        ) as datastore_client:
            value = datastore_service.get_value(name="test1", local=False)
            self.assertTrue(datastore_client.called)
            self.assertEqual(value, kvp1.value)
            self.assertGreater(datastore_service._token_expire, token_expire_time)

    def _set_mock_api_client(self, mock_api_client):
        mock_method = mock.Mock()
        mock_method.return_value = mock_api_client
        self._datastore_service.get_api_client = mock_method
