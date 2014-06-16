import wsmeext.pecan as wsme_pecan
from pecan.rest import RestController
from st2common.models.api.reactor import TriggerAPI, TriggerInstanceAPI
from st2common.persistence.reactor import Trigger, TriggerInstance
from wsme import types as wstypes


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

    @wsme_pecan.wsexpose([TriggerAPI], wstypes.text)
    def get_all(self):
        """
            List all triggers.

            Handles requests:
                GET /triggers/
        """
        return [TriggerAPI.from_model(trigger_db) for
                trigger_db in Trigger.get_all()]


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

    @wsme_pecan.wsexpose([TriggerInstanceAPI], wstypes.text)
    def get_all(self):
        """
            List all triggerinstances.

            Handles requests:
                GET /triggerinstances/
        """
        return [TriggerInstanceAPI.from_model(trigger_instance_db)
                for trigger_instance_db in TriggerInstance.get_all()]
