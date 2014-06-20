import httplib
import wsmeext.pecan as wsme_pecan
from mongoengine import ValidationError
from pecan import abort
from pecan.rest import RestController
from st2common import log as logging
from st2common.models.api.reactor import TriggerAPI, TriggerInstanceAPI
from st2common.persistence.reactor import Trigger, TriggerInstance
from wsme import types as wstypes

LOG = logging.getLogger(__name__)


class TriggerController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Triggers in the system.
    """
    @wsme_pecan.wsexpose(TriggerAPI, wstypes.text)
    def get_one(self, id):

        """
            List triggers by id.

            Handle:
                GET /triggers/1
        """
        LOG.info('GET /triggers/ with id=%s', id)

        try:
            trigger_db = Trigger.get_by_id(id)
        except (ValueError, ValidationError):
            LOG.exception('Database lookup for id="%s" resulted in exception.', id)
            abort(httplib.NOT_FOUND)

        trigger_api = TriggerAPI.from_model(trigger_db)
        LOG.debug('GET /triggers/ with id=%s, client_result=%s', id, trigger_api)
        return trigger_api

    @wsme_pecan.wsexpose([TriggerAPI], wstypes.text)
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
