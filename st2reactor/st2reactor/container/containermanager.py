import os

from st2common import log as logging
from st2common.exceptions.sensors import TriggerTypeRegistrationException
from st2common.models.db.reactor import TriggerDB
from st2common.persistence.reactor import Trigger
from st2common.util import watch
from st2reactor.container.base import SensorContainer
from st2reactor.container.containerservice import ContainerService
import st2reactor.container.utils as container_utils
import six

LOG = logging.getLogger('st2reactor.container.container_manager')


class SensorContainerManager(object):
    # TODO: Load balancing for sensors.
    # TODO: OpLog watcher should be refactored.
    def __init__(self, max_containers=10):
        self._max_containers = max_containers

    def run_sensors(self, sensors_dict):
        LOG.info('Setting up container to run %d sensors.', len(sensors_dict))
        container_service = ContainerService()
        sensors_to_run = []
        trigger_sensors = {}
        for filename, sensors in six.iteritems(sensors_dict):
            for sensor_class in sensors:
                try:
                    sensor = sensor_class(container_service)
                except Exception as e:
                    LOG.warning('Unable to create instance for sensor %s in file %s. Exception: %s',
                                sensor_class, filename, e, exc_info=True)
                    continue

                try:
                    trigger_types = sensor.get_trigger_types()
                    if not trigger_types:
                        LOG.warning('No trigger type registered by sensor %s in file %s',
                                    sensor_class, filename)
                    else:
                        container_utils.add_trigger_models(trigger_types)
                except TriggerTypeRegistrationException as e:
                    LOG.warning('Unable to register trigger type for sensor %s in file %s.'
                                + ' Exception: %s', sensor_class, filename, e, exc_info=True)
                    continue

                for t in trigger_types:
                    trigger_sensors[t['name']] = sensor

                sensors_to_run.append(sensor)

        trigger_names = {}

        for trigger in Trigger.get_all():
            doc = dict(trigger.to_mongo())
            name = trigger.type['name']

            trigger_names[trigger.id] = doc
            if name in trigger_sensors:
                trigger_sensors[name].add_trigger(doc)

        def _watch_insert(ns, ts, op, id, doc):
            name = doc['type']['name']
            parameters = doc['parameters']

            trigger_names[doc['_id']] = doc
            try:
                trigger_sensors[name].add_trigger(doc)
            except KeyError as e:
                if parameters:
                    LOG.warning('Unable to create a trigger %s with parameters %s.'
                                + ' Exception: %s', name, parameters, e, exc_info=True)

        def _watch_update(ns, ts, op, id, doc):
            name = doc['type']['name']
            parameters = doc['parameters']

            trigger_names[doc['_id']] = doc
            try:
                trigger_sensors[name].update_trigger(doc)
            except KeyError as e:
                if parameters:
                    LOG.warning('Unable to update a trigger %s with parameters %s.'
                                + ' Exception: %s', name, parameters, e, exc_info=True)

        def _watch_delete(ns, ts, op, id, doc):
            doc = trigger_names[doc['_id']]
            name = doc['type']['name']

            trigger_sensors[name].remove_trigger(doc)

        LOG.info('Watcher started.')
        watcher = watch.get_watcher()
        watcher.watch(_watch_insert, TriggerDB, watch.INSERT)
        watcher.watch(_watch_update, TriggerDB, watch.UPDATE)
        watcher.watch(_watch_delete, TriggerDB, watch.DELETE)

        LOG.info('SensorContainer process[%s] started.', os.getpid())
        sensor_container = SensorContainer(sensor_instances=sensors_to_run)
        return sensor_container.run()
