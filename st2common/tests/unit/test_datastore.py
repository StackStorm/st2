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


import os
import unittest2

import mock

from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.services.datastore import DatastoreService
from st2client.models.keyvalue import KeyValuePair

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
RESOURCES_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '../resources'))


class DatastoreServiceTestCase(unittest2.TestCase):
    def setUp(self):
        super(DatastoreServiceTestCase, self).setUp()

        self._datastore_service = DatastoreService(logger=mock.Mock(),
                                                   pack_name='core',
                                                   class_name='TestSensor',
                                                   api_username='sensor_service')
        self._datastore_service._get_api_client = mock.Mock()

    def test_datastore_operations_list_values(self):
        # Verify prefix filtering
        mock_api_client = mock.Mock()
        mock_api_client.keys.get_all.return_value = []
        self._set_mock_api_client(mock_api_client)

        self._datastore_service.list_values(local=True, prefix=None)
        mock_api_client.keys.get_all.assert_called_with(prefix='core.TestSensor:')
        self._datastore_service.list_values(local=True, prefix='ponies')
        mock_api_client.keys.get_all.assert_called_with(prefix='core.TestSensor:ponies')

        self._datastore_service.list_values(local=False, prefix=None)
        mock_api_client.keys.get_all.assert_called_with(prefix=None)
        self._datastore_service.list_values(local=False, prefix='ponies')
        mock_api_client.keys.get_all.assert_called_with(prefix='ponies')

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
        kvp1.name = 'test1'
        kvp1.value = 'bar'
        kvp2 = KeyValuePair()
        kvp2.name = 'test2'
        kvp2.value = 'bar'
        mock_return_value = [kvp1, kvp2]
        mock_api_client.keys.get_all.return_value = mock_return_value
        self._set_mock_api_client(mock_api_client)

        values = self._datastore_service.list_values(local=True)
        self.assertEqual(len(values), 2)
        self.assertEqual(values, mock_return_value)

    def test_datastore_operations_get_value(self):
        mock_api_client = mock.Mock()
        kvp1 = KeyValuePair()
        kvp1.name = 'test1'
        kvp1.value = 'bar'
        mock_api_client.keys.get_by_id.return_value = kvp1
        self._set_mock_api_client(mock_api_client)

        value = self._datastore_service.get_value(name='test1', local=False)
        self.assertEqual(value, kvp1.value)

    def test_datastore_operations_set_value(self):
        mock_api_client = mock.Mock()
        mock_api_client.keys.update.return_value = True
        self._set_mock_api_client(mock_api_client)

        value = self._datastore_service.set_value(name='test1', value='foo', local=False)
        self.assertTrue(value)
        kvp = mock_api_client.keys.update.call_args[1]['instance']
        self.assertEquals(kvp.value, 'foo')
        self.assertEquals(kvp.scope, SYSTEM_SCOPE)

    def test_datastore_operations_delete_value(self):
        mock_api_client = mock.Mock()
        mock_api_client.keys.delete.return_value = True
        self._set_mock_api_client(mock_api_client)

        value = self._datastore_service.delete_value(name='test', local=False)
        self.assertTrue(value)

    def test_datastore_operations_set_encrypted_value(self):
        mock_api_client = mock.Mock()
        mock_api_client.keys.update.return_value = True
        self._set_mock_api_client(mock_api_client)
        value = self._datastore_service.set_value(name='test1', value='foo', local=False,
            encrypt=True)
        self.assertTrue(value)
        kvp = mock_api_client.keys.update.call_args[1]['instance']
        self.assertEquals(kvp.value, 'foo')
        self.assertTrue(kvp.secret)
        self.assertEquals(kvp.scope, SYSTEM_SCOPE)

    def test_datastore_unsupported_scope(self):
        self.assertRaises(ValueError, self._datastore_service.get_value, name='test1',
            scope='NOT_SYSTEM')
        self.assertRaises(ValueError, self._datastore_service.set_value, name='test1',
            value='foo', scope='NOT_SYSTEM')
        self.assertRaises(ValueError, self._datastore_service.delete_value, name='test1',
            scope='NOT_SYSTEM')

    def _set_mock_api_client(self, mock_api_client):
        mock_method = mock.Mock()
        mock_method.return_value = mock_api_client
        self._datastore_service._get_api_client = mock_method
