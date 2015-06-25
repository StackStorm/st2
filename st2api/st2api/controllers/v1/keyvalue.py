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

from pecan import abort
from pecan.rest import RestController
import six
from mongoengine import ValidationError

from st2common import log as logging
from st2common.models.api.keyvalue import KeyValuePairAPI
from st2common.models.api.base import jsexpose
from st2common.persistence.keyvalue import KeyValuePair
from st2common.services import coordination

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)

__all__ = [
    'KeyValuePairController'
]


class KeyValuePairController(RestController):
    """
    Implements the REST endpoint for managing the key value store.
    """

    # TODO: Port to use ResourceController
    def __init__(self):
        self._coordinator = coordination.get_coordinator()
        super(KeyValuePairController, self).__init__()

    @jsexpose(arg_types=[str])
    def get_one(self, name):
        """
            List key by name.

            Handle:
                GET /keys/key1
        """
        kvp_db = self.__get_by_name(name=name)

        if not kvp_db:
            LOG.exception('Database lookup for name="%s" resulted in exception.', name)
            abort(http_client.NOT_FOUND)
            return

        try:
            kvp_api = KeyValuePairAPI.from_model(kvp_db)
        except (ValidationError, ValueError) as e:
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        return kvp_api

    @jsexpose(arg_types=[str])
    def get_all(self, **kw):
        """
            List all keys.

            Handles requests:
                GET /keys/
        """
        # Prefix filtering
        prefix_filter = kw.get('prefix', None)

        if prefix_filter:
            kw['name__startswith'] = prefix_filter
            del kw['prefix']

        kvp_dbs = KeyValuePair.get_all(**kw)
        kvps = [KeyValuePairAPI.from_model(kvp_db) for kvp_db in kvp_dbs]

        return kvps

    @jsexpose(arg_types=[str, str], body_cls=KeyValuePairAPI)
    def put(self, name, kvp):
        """
        Create a new entry or update an existing one.
        """
        lock_name = self._get_lock_name_for_key(name=name)

        # Note: We use lock to avoid a race
        with self._coordinator.get_lock(lock_name):
            existing_kvp = self.__get_by_name(name=name)

            kvp.name = name

            try:
                kvp_db = KeyValuePairAPI.to_model(kvp)

                if existing_kvp:
                    kvp_db.id = existing_kvp.id

                kvp_db = KeyValuePair.add_or_update(kvp_db)
            except (ValidationError, ValueError) as e:
                LOG.exception('Validation failed for key value data=%s', kvp)
                abort(http_client.BAD_REQUEST, str(e))
                return

        extra = {'kvp_db': kvp_db}
        LOG.audit('KeyValuePair updated. KeyValuePair.id=%s' % (kvp_db.id), extra=extra)

        kvp_api = KeyValuePairAPI.from_model(kvp_db)
        return kvp_api

    @jsexpose(arg_types=[str], status_code=http_client.NO_CONTENT)
    def delete(self, name):
        """
            Delete the key value pair.

            Handles requests:
                DELETE /keys/1
        """
        lock_name = self._get_lock_name_for_key(name=name)

        # Note: We use lock to avoid a race
        with self._coordinator.get_lock(lock_name):
            kvp_db = self.__get_by_name(name=name)

            if not kvp_db:
                abort(http_client.NOT_FOUND)
                return

            LOG.debug('DELETE /keys/ lookup with name=%s found object: %s', name, kvp_db)

            try:
                KeyValuePair.delete(kvp_db)
            except Exception as e:
                LOG.exception('Database delete encountered exception during '
                              'delete of name="%s". ', name)
                abort(http_client.INTERNAL_SERVER_ERROR, str(e))
                return

        extra = {'kvp_db': kvp_db}
        LOG.audit('KeyValuePair deleted. KeyValuePair.id=%s' % (kvp_db.id), extra=extra)

    @staticmethod
    def __get_by_name(name):
        try:
            return KeyValuePair.get_by_name(name)
        except ValueError as e:
            LOG.debug('Database lookup for name="%s" resulted in exception : %s.', name, e)
            return None

    def _get_lock_name_for_key(self, name):
        """
        Retrieve a coordination lock name for the provided datastore item name.

        :param name: Datastore item name (PK).
        :type name: ``str``
        """
        lock_name = 'kvp-crud-%s' % (name)
        return lock_name
