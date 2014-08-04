import httplib
import wsmeext.pecan as wsme_pecan
from mongoengine import ValidationError, NotUniqueError
from pecan import abort
from pecan.rest import RestController
from st2common import log as logging
from st2common.models.api.reactor import TriggerAPI, TriggerInstanceAPI
from st2common.models.base import jsexpose
from st2common.persistence.reactor import Trigger, TriggerInstance
from wsme import types as wstypes

LOG = logging.getLogger(__name__)


class TriggerController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Triggers in the system.
    """
    # @wsme_pecan.wsexpose(TriggerAPI, wstypes.text)
    def get_one(self, trigger_id):

        """
            List triggers by id.

            Handle:
                GET /triggers/1
        """
        LOG.info('GET /triggers/ with id=%s', id)
        trigger_db = TriggerController.__get_by_id(trigger_id)
        trigger_api = TriggerAPI.from_model(trigger_db)
        LOG.debug('GET /triggers/ with id=%s, client_result=%s', id, trigger_api)
        return trigger_api

    # @wsme_pecan.wsexpose([TriggerAPI], wstypes.text)
    def get_all(self, name=None):
        """
            List all triggers.

            Handles requests:
                GET /triggers/
        """
        LOG.info('GET all /triggers/ and name=%s', name)
        trigger_dbs = Trigger.get_all() if name is None else TriggerController.__get_by_name(name)
        trigger_apis = [TriggerAPI.from_model(trigger_db) for trigger_db in trigger_dbs]
        LOG.debug('GET all /triggers/ client_result=%s', trigger_apis)
        return trigger_apis

    # @wsme_pecan.wsexpose(TriggerAPI, body=TriggerAPI, status_code=httplib.CREATED)
    @jsexpose(body=TriggerAPI, status_code=httplib.CREATED)
    def post(self, trigger):
        """
            Create a new trigger.

            Handles requests:
                POST /triggers/
        """
        LOG.info('POST /triggers/ with trigger data=%s', trigger)

        try:
            trigger_db = TriggerAPI.to_model(trigger)
            LOG.debug('/triggers/ POST verified TriggerAPI and formulated TriggerDB=%s', trigger_db)
            trigger_db = Trigger.add_or_update(trigger_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for trigger data=%s.', trigger)
            abort(httplib.BAD_REQUEST, str(e))
        except NotUniqueError as e:
            LOG.exception('Trigger creation of %s failed with uniqueness conflict.', trigger)
            abort(httplib.CONFLICT, str(e))

        LOG.debug('/triggers/ POST saved TriggerDB object=%s', trigger_db)
        trigger_api = TriggerAPI.from_model(trigger_db)
        LOG.debug('POST /triggers/ client_result=%s', trigger_api)

        return trigger_api

    # @wsme_pecan.wsexpose(TriggerAPI, wstypes.text, body=TriggerAPI, status_code=httplib.OK)
    def put(self, trigger_id, trigger):
        LOG.info('PUT /triggers/ with trigger id=%s and data=%s', trigger_id, trigger)
        trigger_db = TriggerController.__get_by_id(trigger_id)
        LOG.debug('PUT /triggers/ lookup with id=%s found object: %s', trigger_id, trigger_db)

        try:
            if trigger.id is not None and trigger.id is not '' and trigger.id != trigger_id:
                LOG.warning('Discarding mismatched id=%s found in payload and using uri_id=%s.',
                            trigger.id, trigger_id)
            trigger_db = TriggerAPI.to_model(trigger)
            trigger_db.id = trigger_id
            trigger_db = Trigger.add_or_update(trigger_db)
            LOG.debug('/triggers/ PUT updated TriggerDB object=%s', trigger_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for trigger data=%s', trigger)
            abort(httplib.BAD_REQUEST, str(e))

        trigger_api = TriggerAPI.from_model(trigger_db)
        LOG.debug('PUT /triggers/ client_result=%s', trigger_api)

        return trigger_api

    # @wsme_pecan.wsexpose(None, wstypes.text, status_code=httplib.NO_CONTENT)
    def delete(self, trigger_id):
        """
            Delete a trigger.

            Handles requests:
                DELETE /triggers/1
        """
        LOG.info('DELETE /triggers/ with id=%s', trigger_id)
        trigger_db = TriggerController.__get_by_id(trigger_id)
        LOG.debug('DELETE /triggers/ lookup with id=%s found object: %s', trigger_id, trigger_db)
        try:
            Trigger.delete(trigger_db)
        except Exception:
            LOG.exception('Database delete encountered exception during delete of id="%s". ', trigger_id)

    @staticmethod
    def __get_by_id(trigger_id):
        try:
            return Trigger.get_by_id(trigger_id)
        except (ValueError, ValidationError):
            LOG.exception('Database lookup for id="%s" resulted in exception.', trigger_id)
            abort(httplib.NOT_FOUND)

    @staticmethod
    def __get_by_name(trigger_name):
        try:
            return [Trigger.get_by_name(trigger_name)]
        except ValueError as e:
            LOG.debug('Database lookup for name="%s" resulted in exception : %s.', trigger_name, e)
            return []


class TriggerInstanceController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of TriggerInstances in the system.
    """

    @wsme_pecan.wsexpose(TriggerInstanceAPI, wstypes.text)
    def get_one(self, id):
        """
            List triggerinstance by id.

            Handle:
                GET /triggerinstances/1
        """
        LOG.info('GET /triggerinstances/ with id=%s', id)

        try:
            trigger_instance_db = TriggerInstance.get_by_id(id)
        except (ValueError, ValidationError):
            LOG.exception('Database lookup for id="%s" resulted in exception.', id)
            abort(httplib.NOT_FOUND)

        trigger_instance_api = TriggerInstanceAPI.from_model(trigger_instance_db)
        LOG.debug('GET /triggerinstances/ with id=%s, client_result=%s', id, trigger_instance_api)

        return trigger_instance_api

    @wsme_pecan.wsexpose([TriggerInstanceAPI], wstypes.text)
    def get_all(self):
        """
            List all triggerinstances.

            Handles requests:
                GET /triggerinstances/
        """
        LOG.info('GET all /triggerinstances/')
        trigger_instance_apis = [TriggerInstanceAPI.from_model(trigger_instance_db)
                                 for trigger_instance_db in TriggerInstance.get_all()]
        LOG.debug('GET all /triggerinstances/ client_result=%s', trigger_instance_apis)
        return trigger_instance_apis
