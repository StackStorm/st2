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

from st2client.client import Client
from st2client.models import KeyValuePair
from st2common.services.access import create_token
from st2common.util.api import get_full_public_api_url
from st2common.constants.keyvalue import DATASTORE_KEY_SEPARATOR, SYSTEM_SCOPE


class DatastoreService(object):
    """
    Class provides public methods for accessing datastore items.
    """

    DATASTORE_NAME_SEPARATOR = DATASTORE_KEY_SEPARATOR

    def __init__(self, logger, pack_name, class_name, api_username):
        self._api_username = api_username
        self._pack_name = pack_name
        self._class_name = class_name
        self._logger = logger

        self._client = None

    ##################################
    # Methods for datastore management
    ##################################

    def list_values(self, local=True, prefix=None):
        """
        Retrieve all the datastores items.

        :param local: List values from a namespace local to this pack/class. Defaults to True.
        :type: local: ``bool``

        :param prefix: Optional key name prefix / startswith filter.
        :type prefix: ``str``

        :rtype: ``list`` of :class:`KeyValuePair`
        """
        client = self._get_api_client()
        self._logger.audit('Retrieving all the value from the datastore')

        key_prefix = self._get_full_key_prefix(local=local, prefix=prefix)
        kvps = client.keys.get_all(prefix=key_prefix)
        return kvps

    def get_value(self, name, local=True, scope=SYSTEM_SCOPE, decrypt=False):
        """
        Retrieve a value from the datastore for the provided key.

        By default, value is retrieved from the namespace local to the pack/class. If you want to
        retrieve a global value from a datastore, pass local=False to this method.

        :param name: Key name.
        :type name: ``str``

        :param local: Retrieve value from a namespace local to the pack/class. Defaults to True.
        :type: local: ``bool``

        :param scope: Scope under which item is saved. Defaults to system scope.
        :type: local: ``str``

        :param encrypt: Return the decrypted value. Defaults to False.
        :type: local: ``bool``

        :rtype: ``str`` or ``None``
        """
        if scope != SYSTEM_SCOPE:
            raise ValueError('Scope %s is unsupported.' % scope)

        name = self._get_full_key_name(name=name, local=local)

        client = self._get_api_client()
        self._logger.audit('Retrieving value from the datastore (name=%s)', name)

        try:
            params = {'decrypt': str(decrypt).lower(), 'scope': scope}
            kvp = client.keys.get_by_id(id=name, params=params)
        except Exception:
            return None

        if kvp:
            return kvp.value

        return None

    def set_value(self, name, value, ttl=None, local=True, scope=SYSTEM_SCOPE, encrypt=False):
        """
        Set a value for the provided key.

        By default, value is set in a namespace local to the pack/class. If you want to
        set a global value, pass local=False to this method.

        :param name: Key name.
        :type name: ``str``

        :param value: Key value.
        :type value: ``str``

        :param ttl: Optional TTL (in seconds).
        :type ttl: ``int``

        :param local: Set value in a namespace local to the pack/class. Defaults to True.
        :type: local: ``bool``

        :param scope: Scope under which to place the item. Defaults to system scope.
        :type: local: ``str``

        :param encrypt: Encrypyt the value when saving. Defaults to False.
        :type: local: ``bool``

        :return: ``True`` on success, ``False`` otherwise.
        :rtype: ``bool``
        """
        if scope != SYSTEM_SCOPE:
            raise ValueError('Scope %s is unsupported.', scope)

        name = self._get_full_key_name(name=name, local=local)

        value = str(value)
        client = self._get_api_client()

        self._logger.audit('Setting value in the datastore (name=%s)', name)

        instance = KeyValuePair()
        instance.id = name
        instance.name = name
        instance.value = value
        instance.scope = scope
        if encrypt:
            instance.secret = True

        if ttl:
            instance.ttl = ttl

        client.keys.update(instance=instance)
        return True

    def delete_value(self, name, local=True, scope=SYSTEM_SCOPE):
        """
        Delete the provided key.

        By default, value is deleted from a namespace local to the pack/class. If you want to
        delete a global value, pass local=False to this method.

        :param name: Name of the key to delete.
        :type name: ``str``

        :param local: Delete a value in a namespace local to the pack/class. Defaults to True.
        :type: local: ``bool``

        :param scope: Scope under which item is saved. Defaults to system scope.
        :type: local: ``str``

        :return: ``True`` on success, ``False`` otherwise.
        :rtype: ``bool``
        """
        if scope != SYSTEM_SCOPE:
            raise ValueError('Scope %s is unsupported.', scope)

        name = self._get_full_key_name(name=name, local=local)

        client = self._get_api_client()

        instance = KeyValuePair()
        instance.id = name
        instance.name = name

        self._logger.audit('Deleting value from the datastore (name=%s)', name)

        try:
            params = {'scope': scope}
            client.keys.delete(instance=instance, params=params)
        except Exception:
            return False

        return True

    def _get_api_client(self):
        """
        Retrieve API client instance.
        """
        if not self._client:
            ttl = (24 * 60 * 60)
            temporary_token = create_token(username=self._api_username, ttl=ttl)
            api_url = get_full_public_api_url()
            self._client = Client(api_url=api_url, token=temporary_token.token)

        return self._client

    def _get_full_key_name(self, name, local):
        """
        Retrieve a full key name.

        :rtype: ``str``
        """
        if local:
            name = self._get_key_name_with_prefix(name=name)

        return name

    def _get_full_key_prefix(self, local, prefix=None):
        if local:
            key_prefix = self._get_local_key_name_prefix()

            if prefix:
                key_prefix += prefix
        else:
            key_prefix = prefix

        return key_prefix

    def _get_local_key_name_prefix(self):
        """
        Retrieve key prefix which is local to this pack/class.
        """
        key_prefix = self._get_datastore_key_prefix() + self.DATASTORE_NAME_SEPARATOR
        return key_prefix

    def _get_key_name_with_prefix(self, name):
        """
        Retrieve a full key name which is local to the current pack/class.

        :param name: Base datastore key name.
        :type name: ``str``

        :rtype: ``str``
        """
        prefix = self._get_datastore_key_prefix()
        full_name = prefix + self.DATASTORE_NAME_SEPARATOR + name
        return full_name

    def _get_datastore_key_prefix(self):
        prefix = '%s.%s' % (self._pack_name, self._class_name)
        return prefix
