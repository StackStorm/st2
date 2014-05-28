import wsmeext.pecan as wsme_pecan
from mirantis.resource import Resource
from pecan import expose
from pecan.rest import RestController
from st2common.models.api.reactor import TriggerAPI, TriggerInstanceAPI
from st2common.persistence.reactor import Trigger, TriggerInstance
from wsme import types as wstypes


class TriggersAPI(Resource):
    triggers = [TriggerAPI]


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
        trigger_db = Trigger.get_by_id(id)
        return TriggerAPI.from_model(trigger_db)

    @wsme_pecan.wsexpose(TriggersAPI, wstypes.text)
    def get_all(self):
        """ 
            List all triggers.

            Handles requests:
                GET /triggers/
        """
        triggers = TriggersAPI()
        triggers.triggers = [TriggerAPI.from_model(trigger_db) for
                             trigger_db in Trigger.get_all()]
        return triggers


class TriggerInstancesAPI(Resource):
    trigger_instances = [TriggerInstanceAPI]


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
        trigger_instance_db = TriggerInstance.get_by_id(id)
        return TriggerInstanceAPI.from_model(trigger_instance_db)

    @wsme_pecan.wsexpose(TriggerInstancesAPI, wstypes.text)
    def get_all(self):
        """
            List all triggerinstances.

            Handles requests:
                GET /triggerinstances/
        """
        trigger_instances = TriggerInstancesAPI()
        trigger_instances.trigger_instances = [
            TriggerInstanceAPI.from_model(trigger_instance_db)
            for trigger_instance_db in TriggerInstance.get_all()]
        return trigger_instances
