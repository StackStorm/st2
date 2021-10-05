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
from datetime import timedelta

from oslo_config import cfg

from st2client.client import Client
from st2client.models.keyvalue import KeyValuePair
from st2common.util.api import get_full_public_api_url
from st2common.util.date import get_datetime_utc_now
from st2common.constants.keyvalue import DATASTORE_KEY_SEPARATOR, SYSTEM_SCOPE

__all__ = ["BaseDatastoreService", "ActionDatastoreService", "SensorDatastoreService"]


class BaseDatastoreService(object):
    """
    Base DatastoreService class which provides public methods for accessing datastore items.
    """

    DATASTORE_NAME_SEPARATOR = DATASTORE_KEY_SEPARATOR

    def __init__(self, logger, pack_name, class_name):
        """
        :param auth_token: Auth token used to authenticate with StackStorm API.
        :type auth_token: ``str``
        """
        self._pack_name = pack_name
        self._class_name = class_name
        self._logger = logger

        self._client = None
        self._token_expire = get_datetime_utc_now()

    ##################################
    # General methods
    ##################################

    def get_user_info(self):
        """
        Retrieve information about the current user which is authenticated against StackStorm and
        used to perform other datastore operations via the API.

        :rtype: ``dict``
        """
        client = self.get_api_client()

        self._logger.debug("Retrieving user information")

        result = client.get_user_info()
        return result

    ##################################
    # Methods for datastore management
    ##################################

    def list_values(self, local=True, prefix=None, limit=None, offset=0):
        """
        Retrieve all the datastores items.

        :param local: List values from a namespace local to this pack/class. Defaults to True.
        :type: local: ``bool``

        :param prefix: Optional key name prefix / startswith filter.
        :type prefix: ``str``

        :param limit: Number of keys to get. Defaults to the configuration set at 'api.max_page_size'.
        :type limit: ``integer``

        :param offset: Number of keys to offset. Defaults to 0.
        :type offset: ``integer``

        :rtype: ``list`` of :class:`KeyValuePair`
        """
        client = self.get_api_client()
        self._logger.debug("Retrieving all the values from the datastore")

        limit = limit or cfg.CONF.api.max_page_size
        key_prefix = self._get_full_key_prefix(local=local, prefix=prefix)
        kvps = client.keys.get_all(prefix=key_prefix, limit=limit, offset=offset)
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

        :param decrypt: Return the decrypted value. Defaults to False.
        :type: local: ``bool``

        :rtype: ``str`` or ``None``
        """
        if scope != SYSTEM_SCOPE:
            raise ValueError("Scope %s is unsupported." % scope)

        name = self._get_full_key_name(name=name, local=local)

        client = self.get_api_client()
        self._logger.debug("Retrieving value from the datastore (name=%s)", name)

        try:
            params = {"decrypt": str(decrypt).lower(), "scope": scope}
            kvp = client.keys.get_by_id(id=name, params=params)
        except Exception as e:
            self._logger.exception(
                "Exception retrieving value from datastore (name=%s): %s", name, e
            )
            return None

        if kvp:
            return kvp.value

        return None

    def set_value(
        self, name, value, ttl=None, local=True, scope=SYSTEM_SCOPE, encrypt=False
    ):
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

        :param encrypt: Encrypt the value when saving. Defaults to False.
        :type: local: ``bool``

        :return: ``True`` on success, ``False`` otherwise.
        :rtype: ``bool``
        """
        if scope != SYSTEM_SCOPE:
            raise ValueError("Scope %s is unsupported." % scope)

        name = self._get_full_key_name(name=name, local=local)

        value = str(value)
        client = self.get_api_client()

        self._logger.debug("Setting value in the datastore (name=%s)", name)

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
            raise ValueError("Scope %s is unsupported." % scope)

        name = self._get_full_key_name(name=name, local=local)

        client = self.get_api_client()

        instance = KeyValuePair()
        instance.id = name
        instance.name = name

        self._logger.debug("Deleting value from the datastore (name=%s)", name)

        try:
            params = {"scope": scope}
            client.keys.delete(instance=instance, params=params)
        except Exception as e:
            self._logger.exception(
                "Exception deleting value from datastore (name=%s): %s", name, e
            )
            return False

        return True

    def get_api_client(self):
        """
        Retrieve API client instance.
        """
        raise NotImplementedError("get_api_client() not implemented")

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
        prefix = "%s.%s" % (self._pack_name, self._class_name)
        return prefix


class ActionDatastoreService(BaseDatastoreService):
    """
    DatastoreService class used by actions. This class uses temporary auth token which is generated
    by the runner container service and available for the duration of the lifetime of an action.

    Note: This class does NOT need database access.
    """

    def __init__(self, logger, pack_name, class_name, auth_token):
        """
        :param auth_token: Auth token used to authenticate with StackStorm API.
        :type auth_token: ``str``
        """
        super(ActionDatastoreService, self).__init__(
            logger=logger, pack_name=pack_name, class_name=class_name
        )

        self._auth_token = auth_token
        self._client = None

    def get_api_client(self):
        """
        Retrieve API client instance.
        """
        if not self._client:
            self._logger.debug("Creating new Client object.")

            api_url = get_full_public_api_url()
            client = Client(api_url=api_url, token=self._auth_token)
            self._client = client

        return self._client


class SensorDatastoreService(BaseDatastoreService):
    """
    DatastoreService class used by sensors. This class is meant to be used in context of long
    running processes (e.g. sensors) and it uses "create_token" method to generate a new auth
    token. A new token is also automatically generated once the old one expires.

    Note: This class does need database access (create_token method - to be able to create a new
    token).
    """

    def __init__(self, logger, pack_name, class_name, api_username):
        super(SensorDatastoreService, self).__init__(
            logger=logger, pack_name=pack_name, class_name=class_name
        )
        self._api_username = api_username
        self._token_expire = get_datetime_utc_now()

    def get_api_client(self):
        """
        Retrieve API client instance.
        """
        token_expire = self._token_expire <= get_datetime_utc_now()

        if not self._client or token_expire:
            # Note: Late import to avoid high import cost (time wise)
            from st2common.services.access import create_token

            self._logger.debug("Creating new Client object.")

            ttl = cfg.CONF.auth.service_token_ttl
            api_url = get_full_public_api_url()

            temporary_token = create_token(
                username=self._api_username, ttl=ttl, service=True
            )
            self._client = Client(api_url=api_url, token=temporary_token.token)
            self._token_expire = get_datetime_utc_now() + timedelta(seconds=ttl)

        return self._client
