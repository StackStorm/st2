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
    def get_one(self, name):
        """
            List key by name.

            Handle:
                GET /keys/key1
        """
        LOG.info('GET /keys/ with name=%s', name)

        kvp_db = self.__get_by_name(name=name)

        if not kvp_db:
            LOG.exception('Database lookup for name="%s" '
                          'resulted in exception.', name)
            abort(http_client.NOT_FOUND)
            return

        try:
            kvp_api = KeyValuePairAPI.from_model(kvp_db)
        except (ValidationError, ValueError) as e:
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        LOG.debug('GET /keys/ with name=%s, client_result=%s', name, kvp_api)
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

    @jsexpose(str, body=KeyValuePairAPI)
    def put(self, name, kvp):
        """
        Create a new entry or update an existing one.
        """
        LOG.info('PUT /keys/ with key name=%s and data=%s', name, kvp)

        # TODO: There is a race, add custom add_or_update which updates by non
        # id field
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

        LOG.audit('KeyValuePair updated. KeyValuePair=%s', kvp_db)
        kvp_api = KeyValuePairAPI.from_model(kvp_db)
        LOG.debug('PUT /keys/ client_result=%s', kvp_api)

        return kvp_api

    @jsexpose(str, status_code=http_client.NO_CONTENT)
    def delete(self, name):
        """
            Delete the key value pair.

            Handles requests:
                DELETE /keys/1
        """
        LOG.info('DELETE /keys/ with id=%s', id)
        kvp_db = self.__get_by_name(name=name)

        if not kvp_db:
            LOG.exception('Database lookup for name="%s" '
                          'resulted in exception.', name)
            abort(http_client.NOT_FOUND)
            return

        LOG.debug('DELETE /keys/ lookup with name=%s found '
                  'object: %s', name, kvp_db)
        try:
            KeyValuePair.delete(kvp_db)
        except Exception as e:
            LOG.exception('Database delete encountered exception during '
                          'delete of name="%s". ', name)
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        LOG.audit('KeyValuePair deleted. KeyValuePair=%s', kvp_db)

    @staticmethod
    def __get_by_name(name):
        try:
            return KeyValuePair.get_by_name(name)
        except ValueError as e:
            LOG.debug('Database lookup for name="%s" '
                      'resulted in exception : %s.', name, e)
            return None
