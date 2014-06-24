import datetime

from st2common import log as logging
import st2reactor.container.utils as container_utils
import st2reactor.ruleenforcement.enforce as rules_engine

LOG = logging.getLogger('st2reactor.sensor.dispatcher')


class TriggerDispatcher(object):

    def __init__(self):
        pass

    def dispatch(self, triggers):
        """
        """
        trigger_instances = []
        for trigger in triggers:
            ti = container_utils.create_trigger_instance(
                trigger['name'],
                trigger['payload'] if 'payload' in trigger else {},
                trigger['occurrence_time'] if 'occurrence_time' in trigger else
                datetime.datetime.now())
            if ti is not None:
                trigger_instances.append(ti)

        if trigger_instances:
            rules_engine.handle_trigger_instances(trigger_instances)
