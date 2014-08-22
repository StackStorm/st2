import httplib
import wsmeext.pecan as wsme_pecan
from mongoengine import ValidationError, NotUniqueError
from pecan import abort
from pecan.rest import RestController
from st2common import log as logging
from st2common.models.api.reactor import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI
from st2common.models.base import jsexpose
from st2common.persistence.reactor import TriggerType, Trigger, TriggerInstance
from st2api.service import triggers as TriggerService
from wsme import types as wstypes

LOG = logging.getLogger(__name__)


class TriggerTypeController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of TriggerTypes in the system.
    """
    @jsexpose(str)
    def get_one(self, triggertype_id):

        """
            List triggertypes by id.

            Handle:
                GET /triggertypes/1
        """
        LOG.info('GET /triggertypes/ with id=%s', id)
        triggertype_db = TriggerTypeController.__get_by_id(triggertype_id)
        triggertype_api = TriggerTypeAPI.from_model(triggertype_db)
        LOG.debug('GET /triggertypes/ with id=%s, client_result=%s', id, triggertype_api)
        return triggertype_api

    @jsexpose(str)
    def get_all(self, name=None):
        """
            List all triggertypes.

            Handles requests:
                GET /triggertypes/
        """
        LOG.info('GET all /triggertypes/ and name=%s', name)
        triggertype_dbs = TriggerType.get_all() if name is None else \
            TriggerTypeController.__get_by_name(name)
        triggertype_apis = [TriggerTypeAPI.from_model(triggertype_db) for triggertype_db in
                            triggertype_dbs]
        LOG.debug('GET all /triggertypes/ client_result=%s', triggertype_apis)
        return triggertype_apis

    @jsexpose(body=TriggerTypeAPI, status_code=httplib.CREATED)
    def post(self, triggertype):
        """
            Create a new triggertype.

            Handles requests:
                POST /triggertypes/
        """
        LOG.info('POST /triggertypes/ with triggertype data=%s', triggertype)

        try:
            triggertype_db = TriggerTypeAPI.to_model(triggertype)
            LOG.debug('/triggertypes/ POST verified TriggerTypeAPI and formulated TriggerTypeDB=%s',
                      triggertype_db)
            triggertype_db = TriggerType.add_or_update(triggertype_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for triggertype data=%s.', triggertype)
            abort(httplib.BAD_REQUEST, str(e))
        except NotUniqueError as e:
            LOG.warn('TriggerType creation of %s failed with uniqueness conflict. Exception : %s',
                     triggertype, str(e))
            abort(httplib.CONFLICT, str(e))

        LOG.audit('TriggerType created. TriggerType=%s', triggertype_db)
        triggertype_api = TriggerTypeAPI.from_model(triggertype_db)
        LOG.debug('POST /triggertypes/ client_result=%s', triggertype_api)

        return triggertype_api

    @jsexpose(str, body=TriggerTypeAPI)
    def put(self, triggertype_id, triggertype):
        LOG.info('PUT /triggertypes/ with triggertype id=%s and data=%s', triggertype_id,
                 triggertype)
        triggertype_db = TriggerTypeController.__get_by_id(triggertype_id)
        LOG.debug('PUT /triggertypes/ lookup with id=%s found object: %s', triggertype_id,
                  triggertype_db)
        try:
            triggertype_db = TriggerTypeAPI.to_model(triggertype)
            if triggertype.id is not None and len(triggertype.id) > 0 and \
               triggertype.id != triggertype_id:
                LOG.warning('Discarding mismatched id=%s found in payload and using uri_id=%s.',
                            triggertype.id, triggertype_id)
            triggertype_db.id = triggertype_id
            old_triggertype_db = triggertype_db
            triggertype_db = TriggerType.add_or_update(triggertype_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for triggertype data=%s', triggertype)
            abort(httplib.BAD_REQUEST, str(e))

        LOG.audit('TriggerType updated. TriggerType=%s and original TriggerType=%s',
                  triggertype_db, old_triggertype_db)
        triggertype_api = TriggerTypeAPI.from_model(triggertype_db)
        LOG.debug('PUT /triggertypes/ client_result=%s', triggertype_api)

        return triggertype_api

    @jsexpose(str, status_code=httplib.NO_CONTENT)
    def delete(self, triggertype_id):
        """
            Delete a triggertype.

            Handles requests:
                DELETE /triggertypes/1
        """
        LOG.info('DELETE /triggertypes/ with id=%s', triggertype_id)
        triggertype_db = TriggerTypeController.__get_by_id(triggertype_id)
        LOG.debug('DELETE /triggertypes/ lookup with id=%s found object: %s', triggertype_id,
                  triggertype_db)
        try:
            TriggerType.delete(triggertype_db)
        except Exception as e:
            LOG.exception('Database delete encountered exception during delete of id="%s". ',
                          triggertype_id)
            abort(httplib.INTERNAL_SERVER_ERROR, str(e))
        LOG.audit('TriggerType deleted. TriggerType=%s', triggertype_db)

    @staticmethod
    def __get_by_id(triggertype_id):
        try:
            return TriggerType.get_by_id(triggertype_id)
        except (ValueError, ValidationError):
            LOG.exception('Database lookup for id="%s" resulted in exception.', triggertype_id)
            abort(httplib.NOT_FOUND)

    @staticmethod
    def __get_by_name(triggertype_name):
        try:
            return [TriggerType.get_by_name(triggertype_name)]
        except ValueError as e:
            LOG.debug('Database lookup for name="%s" resulted in exception : %s.',
                      triggertype_name, e)
            return []


class TriggerController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Triggers in the system.
    """
    @jsexpose(str)
    def get_one(self, trigger_id):

        """
            List triggertypes by id.

            Handle:
                GET /triggertypes/1
        """
        LOG.info('GET /triggers/ with id=%s', id)
        trigger_db = TriggerController.__get_by_id(trigger_id)
        trigger_api = TriggerAPI.from_model(trigger_db)
        LOG.debug('GET /triggers/ with id=%s, client_result=%s', id, trigger_api)
        return trigger_api

    @jsexpose(str)
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

    @jsexpose(body=TriggerAPI, status_code=httplib.CREATED)
    def post(self, trigger):
        """
            Create a new trigger.

            Handles requests:
                POST /triggers/
        """
        LOG.info('POST /triggers/ with trigger data=%s', trigger)

        try:
            trigger_db = TriggerService.create_trigger_db(trigger)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for trigger data=%s.', trigger)
            abort(httplib.BAD_REQUEST, str(e))
        except NotUniqueError as e:
            LOG.warn('Trigger creation of %s failed with uniqueness conflict. Exception %s',
                     trigger, str(e))
            abort(httplib.CONFLICT, str(e))

        LOG.audit('Trigger created. Trigger=%s', trigger_db)
        trigger_api = TriggerAPI.from_model(trigger_db)
        LOG.debug('POST /triggers/ client_result=%s', trigger_api)

        return trigger_api

    @jsexpose(str, body=TriggerAPI)
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
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for trigger data=%s', trigger)
            abort(httplib.BAD_REQUEST, str(e))

        LOG.audit('Trigger updated. Trigger=%s and original Trigger=%s.', trigger_db)
        trigger_api = TriggerAPI.from_model(trigger_db)
        LOG.debug('PUT /triggers/ client_result=%s', trigger_api)

        return trigger_api

    @jsexpose(str, status_code=httplib.NO_CONTENT)
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
        except Exception as e:
            LOG.exception('Database delete encountered exception during delete of id="%s". ',
                          trigger_id)
            abort(httplib.INTERNAL_SERVER_ERROR, str(e))
        LOG.audit('Trigger deleted. Trigger=%s', trigger_db)

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
