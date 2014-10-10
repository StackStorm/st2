import datetime

from st2common import log as logging
import st2reactor.container.utils as container_utils
from st2reactor.rules.engine import RulesEngine

LOG = logging.getLogger('st2reactor.sensor.dispatcher')


class TriggerDispatcher(object):

    def __init__(self):
        self.rules_engine = RulesEngine()

    def dispatch(self, trigger, payload=None):
        """
        """
        trigger_instance = container_utils.create_trigger_instance(
            trigger,
            payload or {},
            datetime.datetime.utcnow())

        if trigger_instance:
            self.rules_engine.handle_trigger_instance(trigger_instance)
