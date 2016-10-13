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

"""
Mock classes for use in pack testing.
"""

from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.services.datastore import DatastoreService
from st2client.models.keyvalue import KeyValuePair

__all__ = [
    'MockDatastoreService'
]


class MockDatastoreService(DatastoreService):
    """
    Mock DatastoreService for use in testing.
    """
    def __init__(self, logger, pack_name, class_name, api_username):
        self._pack_name = pack_name
        self._class_name = class_name

        # Holds mock KeyValuePair objects
        # Key is a KeyValuePair name and value is the KeyValuePair object
        self._datastore_items = {}

    def list_values(self, local=True, prefix=None):
        """
        Return a list of all values stored in a dictionary which is local to this class.
        """
        key_prefix = self._get_full_key_prefix(local=local, prefix=prefix)

        if not key_prefix:
            return self._datastore_items.values()

        result = []
        for name, kvp in self._datastore_items.items():
            if name.startswith(key_prefix):
                result.append(kvp)

        return result

    def get_value(self, name, local=True, scope=SYSTEM_SCOPE, decrypt=False):
        """
        Return a particular value stored in a dictionary which is local to this class.
        """
        name = self._get_full_key_name(name=name, local=local)

        if name not in self._datastore_items:
            return None

        kvp = self._datastore_items[name]
        return kvp.value

    def set_value(self, name, value, ttl=None, local=True, scope=SYSTEM_SCOPE, encrypt=False):
        """
        Store a value in a dictionary which is local to this class.
        """
        if ttl:
            raise ValueError('MockDatastoreService.set_value doesn\'t support "ttl" argument')

        name = self._get_full_key_name(name=name, local=local)

        instance = KeyValuePair()
        instance.id = name
        instance.name = name
        instance.value = value

        self._datastore_items[name] = instance
        return True

    def delete_value(self, name, local=True, scope=SYSTEM_SCOPE):
        """
        Delete a value from a dictionary which is local to this class.
        """
        name = self._get_full_key_name(name=name, local=local)

        if name not in self._datastore_items:
            return False

        del self._datastore_items[name]
        return True
