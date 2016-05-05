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
import six
from mongoengine import ValidationError

from st2api.controllers.resource import ResourceController
from st2common import log as logging
from st2common.constants.system import SYSTEM_KV_PREFIX
from st2common.exceptions.keyvalue import CryptoKeyNotSetupException, InvalidScopeException
from st2common.models.api.keyvalue import KeyValuePairAPI
from st2common.models.api.base import jsexpose
from st2common.persistence.keyvalue import KeyValuePair
from st2common.services import coordination

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)

__all__ = [
    'KeyValuePairController'
]


class KeyValuePairController(ResourceController):
    """
    Implements the REST endpoint for managing the key value store.
    """

    model = KeyValuePairAPI
    access = KeyValuePair
    supported_filters = {
        'prefix': 'name__startswith',
        'scope': 'scope'
    }

    def __init__(self):
        super(KeyValuePairController, self).__init__()
        self._coordinator = coordination.get_coordinator()
        self.get_one_db_method = self._get_by_name

    @jsexpose(arg_types=[str, str, bool])
    def get_one(self, name, scope=SYSTEM_KV_PREFIX, decrypt=False):
        """
            List key by name.

            Handle:
                GET /keys/key1
        """
        from_model_kwargs = {'mask_secrets': not decrypt}
        if scope:
            kwargs = {'name': name, 'scope': scope}
            kvp_db = super(KeyValuePairController, self)._get_all(
                from_model_kwargs=from_model_kwargs,
                **kwargs
            )
            kvp_db = kvp_db[0] if kvp_db else None
            if not kvp_db:
                msg = 'Key with name: %s and scope: %s not found!' % (name, scope)
                abort(http_client.NOT_FOUND, msg)
                return
        else:
            kvp_db = super(KeyValuePairController, self)._get_one_by_name_or_id(
                name_or_id=name,
                from_model_kwargs=from_model_kwargs
            )
        return kvp_db

    @jsexpose(arg_types=[str, str, bool])
    def get_all(self, prefix=None, scope=SYSTEM_KV_PREFIX, decrypt=False, **kwargs):
        """
            List all keys.

            Handles requests:
                GET /keys/
        """
        from_model_kwargs = {'mask_secrets': not decrypt}
        kwargs['prefix'] = prefix
        kwargs['scope'] = scope
        kvp_dbs = super(KeyValuePairController, self)._get_all(from_model_kwargs=from_model_kwargs,
                                                               **kwargs)
        return kvp_dbs

    @jsexpose(arg_types=[str, str], body_cls=KeyValuePairAPI)
    def put(self, name, kvp):
        """
        Create a new entry or update an existing one.
        """
        lock_name = self._get_lock_name_for_key(name=name)

        # TODO: Custom permission check since the key doesn't need to exist here

        # Note: We use lock to avoid a race
        with self._coordinator.get_lock(lock_name):
            existing_kvp = self._get_by_name(resource_name=name)

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
            except CryptoKeyNotSetupException as e:
                LOG.exception(str(e))
                abort(http_client.BAD_REQUEST, str(e))
                return
            except InvalidScopeException as e:
                LOG.exception(str(e))
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
            kvp_db = self._get_by_name(resource_name=name)

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

    def _get_lock_name_for_key(self, name):
        """
        Retrieve a coordination lock name for the provided datastore item name.

        :param name: Datastore item name (PK).
        :type name: ``str``
        """
        lock_name = 'kvp-crud-%s' % (name)
        return lock_name
