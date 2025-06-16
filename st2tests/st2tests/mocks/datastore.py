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

"""
Mock classes for use in pack testing.
"""

from __future__ import absolute_import
from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.services.datastore import BaseDatastoreService
from st2client.models.keyvalue import KeyValuePair

__all__ = ["MockDatastoreService"]


class MockDatastoreService(BaseDatastoreService):
    """
    Mock DatastoreService for use in testing.
    """

    def __init__(self, logger, pack_name, class_name, api_username=None):
        self._pack_name = pack_name
        self._class_name = class_name
        self._username = api_username or "admin"
        self._logger = logger

        # Holds mock KeyValuePair objects
        # Key is a KeyValuePair name and value is the KeyValuePair object
        self._datastore_items = {}

    ##################################
    # General methods
    ##################################

    def get_user_info(self):
        """
        Retrieve information about the current user which is authenticated against StackStorm and
        used to perform other datastore operations via the API.

        :rtype: ``dict``
        """
        result = {
            "username": self._username,
            "rbac": {"is_admin": True, "enabled": True, "roles": ["admin"]},
            "authentication": {"method": "authentication token", "location": "header"},
        }

        return result

    ##################################
    # Methods for datastore management
    ##################################

    def list_values(self, local=True, limit=None, prefix=None, offset=0):
        """
        Return a list of all values stored in a dictionary which is local to this class.
        """
        key_prefix = self._get_full_key_prefix(local=local, prefix=prefix)

        if not key_prefix:
            return list(self._datastore_items.values())

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

    def set_value(
        self, name, value, ttl=None, local=True, scope=SYSTEM_SCOPE, encrypt=False
    ):
        """
        Store a value in a dictionary which is local to this class.
        """

        name = self._get_full_key_name(name=name, local=local)

        instance = KeyValuePair()
        instance.id = name
        instance.name = name
        instance.value = value
        if ttl:
            self._logger.warning(
                "MockDatastoreService is not able to expire keys based on ttl."
            )
            instance.ttl = ttl

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
