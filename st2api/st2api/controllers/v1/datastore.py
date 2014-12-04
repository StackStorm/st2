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
from st2common.models.api.datastore import KeyValuePairAPI
from st2common.models.base import jsexpose
from st2common.persistence.datastore import KeyValuePair

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class KeyValuePairController(RestController):
    """
    Implements the REST endpoint for managing the key value store.
    """

    @jsexpose(str)
    def get_one(self, id):
        """
            List key by id.

            Handle:
                GET /keys/1
        """
        LOG.info('GET /keys/ with id=%s', id)
        kvp_db = self.__get_by_id(id)

        try:
            kvp_api = KeyValuePairAPI.from_model(kvp_db)
        except (ValidationError, ValueError) as e:
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        LOG.debug('GET /keys/ with id=%s, client_result=%s', id, kvp_api)
        return kvp_api

    @jsexpose(str)
    def get_all(self, **kw):
        """
            List all keys.

            Handles requests:
                GET /keys/
        """
        LOG.info('GET all /keys/ with filters=%s', kw)

        kvp_dbs = KeyValuePair.get_all(**kw)
        kvps = [KeyValuePairAPI.from_model(kvp_db) for kvp_db in kvp_dbs]
        LOG.debug('GET all /keys/ client_result=%s', kvps)

        return kvps

    @jsexpose(body=KeyValuePairAPI, status_code=http_client.CREATED)
    def post(self, kvp):
        """
            Create a new key value pair.

            Handles requests:
                POST /keys/
        """
        LOG.info('POST /keys/ with key value data=%s', kvp)

        try:
            kvp_db = KeyValuePairAPI.to_model(kvp)
            LOG.debug('/keys/ POST verified KeyValuePairAPI and '
                      'formulated KeyValuePairDB=%s', kvp_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for key value data=%s.', kvp)
            abort(http_client.BAD_REQUEST, str(e))
            return

        kvp_db = KeyValuePair.add_or_update(kvp_db)
        LOG.audit('KeyValuePair created. KeyValuePair=%s', kvp_db)

        kvp_api = KeyValuePairAPI.from_model(kvp_db)
        LOG.debug('POST /keys/ client_result=%s', kvp_api)

        return kvp_api

    @jsexpose(str, body=KeyValuePairAPI)
    def put(self, id, kvp):
        LOG.info('PUT /keys/ with key id=%s and data=%s', id, kvp)
        kvp_db = self.__get_by_id(id)
        LOG.debug('PUT /keys/ lookup with id=%s found object: %s', id, kvp_db)

        try:
            if kvp.id and kvp.id != id:
                LOG.warning('Discarding mismatched id=%s found in payload '
                            'and using uri_id=%s.',
                            kvp.id, id)
            old_kvp_db = kvp_db
            kvp_db = KeyValuePairAPI.to_model(kvp)
            kvp_db.id = id
            kvp_db = KeyValuePair.add_or_update(kvp_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for key value data=%s', kvp)
            abort(http_client.BAD_REQUEST, str(e))
            return

        LOG.audit('KeyValuePair updated. KeyValuePair=%s and original KeyValuePair=%s',
                  kvp_db, old_kvp_db)
        kvp_api = KeyValuePairAPI.from_model(kvp_db)
        LOG.debug('PUT /keys/ client_result=%s', kvp_api)

        return kvp_api

    @jsexpose(str, status_code=http_client.NO_CONTENT)
    def delete(self, id):
        """
            Delete the key value pair.

            Handles requests:
                DELETE /keys/1
        """
        LOG.info('DELETE /keys/ with id=%s', id)
        kvp_db = self.__get_by_id(id)
        LOG.debug('DELETE /keys/ lookup with id=%s found '
                  'object: %s', id, kvp_db)
        try:
            KeyValuePair.delete(kvp_db)
        except Exception as e:
            LOG.exception('Database delete encountered exception during '
                          'delete of id="%s". ', id)
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        LOG.audit('KeyValuePair deleted. KeyValuePair=%s', kvp_db)

    @staticmethod
    def __get_by_id(id):
        try:
            return KeyValuePair.get_by_id(id)
        except Exception:
            LOG.exception('Database lookup for id="%s" '
                          'resulted in exception.', id)
            abort(http_client.NOT_FOUND)

    @staticmethod
    def __get_by_name(name):
        try:
            return [KeyValuePair.get_by_name(name)]
        except ValueError as e:
            LOG.debug('Database lookup for name="%s" '
                      'resulted in exception : %s.', name, e)
            return []
