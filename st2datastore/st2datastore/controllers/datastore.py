import httplib
from pecan import abort
from pecan.rest import RestController
import wsmeext.pecan as wsme_pecan
from wsme import types as wstypes
from mongoengine import ValidationError

from st2common import log as logging
from st2common.models.api.datastore import KeyValuePairAPI
from st2common.persistence.datastore import KeyValuePair


LOG = logging.getLogger(__name__)


class KeyValuePairController(RestController):
    """
    Implements the REST endpoint for managing the key value store.
    """

    @wsme_pecan.wsexpose(KeyValuePairAPI, wstypes.text)
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
            abort(httplib.INTERNAL_SERVER_ERROR, str(e))
        LOG.debug('GET /keys/ with id=%s, client_result=%s', id, kvp_api)
        return kvp_api

    @wsme_pecan.wsexpose([KeyValuePairAPI], wstypes.text)
    def get_all(self, name=None):
        """
            List all keys.

            Handles requests:
                GET /keys/
        """
        LOG.info('GET all /keys/ and name=%s', str(name))

        kvp_dbs = (KeyValuePair.get_all()
                   if name is None else self.__get_by_name(name))

        kvps = [KeyValuePairAPI.from_model(kvp_db) for kvp_db in kvp_dbs]

        LOG.debug('GET all /keys/ client_result=%s', kvps)

        return kvps

    @wsme_pecan.wsexpose(KeyValuePairAPI, body=KeyValuePairAPI,
                         status_code=httplib.CREATED)
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
            abort(httplib.BAD_REQUEST, str(e))

        kvp_db = KeyValuePair.add_or_update(kvp_db)
        LOG.debug('/keys/ POST saved KeyValuePairDB object=%s', kvp_db)

        kvp_api = KeyValuePairAPI.from_model(kvp_db)
        LOG.debug('POST /keys/ client_result=%s', kvp_api)

        return kvp_api

    @wsme_pecan.wsexpose(KeyValuePairAPI, wstypes.text, body=KeyValuePairAPI)
    def put(self, id, kvp):
        LOG.info('PUT /keys/ with key id=%s and data=%s', id, kvp)
        kvp_db = self.__get_by_id(id)
        LOG.debug('PUT /keys/ lookup with id=%s found object: %s', id, kvp_db)

        try:
            if kvp.id and kvp.id != id:
                LOG.warning('Discarding mismatched id=%s found in payload '
                            'and using uri_id=%s.',
                            kvp.id, id)
            kvp_db = KeyValuePairAPI.to_model(kvp)
            kvp_db.id = id
            kvp_db = KeyValuePair.add_or_update(kvp_db)
            LOG.debug('/keys/ PUT updated KeyValuePairDB object=%s', kvp_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for key value data=%s', kvp)
            abort(httplib.BAD_REQUEST, str(e))

        kvp_api = KeyValuePairAPI.from_model(kvp_db)
        LOG.debug('PUT /keys/ client_result=%s', kvp_api)

        return kvp_api

    @wsme_pecan.wsexpose(None, wstypes.text, status_code=httplib.NO_CONTENT)
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
            abort(httplib.INTERNAL_SERVER_ERROR, str(e))

    @staticmethod
    def __get_by_id(id):
        try:
            return KeyValuePair.get_by_id(id)
        except Exception:
            LOG.exception('Database lookup for id="%s" '
                          'resulted in exception.', id)
            abort(httplib.NOT_FOUND)

    @staticmethod
    def __get_by_name(name):
        try:
            return [KeyValuePair.get_by_name(name)]
        except ValueError as e:
            LOG.debug('Database lookup for name="%s" '
                      'resulted in exception : %s.', name, e)
            return []
