try:
    import simplejson as json
except ImportError:
    import json
import os
import sys


from st2common import log as logging
from st2common.exceptions.sensors import TriggerTypeRegistrationException
from st2common.persistence.reactor import Trigger
from st2reactor.container.base import SensorContainer
from st2reactor.container.service import ContainerService
from st2reactor.container.triggerwatcher import TriggerWatcher
import st2reactor.container.utils as container_utils
import six

LOG = logging.getLogger(__name__)


class SensorContainerManager(object):
    # TODO: Load balancing for sensors.
    def __init__(self, max_containers=10):
        self._max_containers = max_containers
        self._trigger_names = {}
        self._trigger_sensors = {}
        self._trigger_watcher = TriggerWatcher(self._create_handler,
                                               self._update_handler,
                                               self._delete_handler)

    def run_sensors(self, sensors_dict):
        LOG.info('Setting up container to run %d sensors.', len(sensors_dict))
        container_service = ContainerService()
        sensors_to_run = []
        for filename, sensors in six.iteritems(sensors_dict):
            for sensor_class in sensors:
                try:
                    config = self._get_config(filename)
                    sensor = sensor_class(container_service, **config)
                    setattr(sensor, 'config', config)
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
                    self._trigger_sensors[t['name']] = sensor

                sensors_to_run.append(sensor)

        for trigger in Trigger.get_all():
            self._create_handler(trigger)

        self._trigger_watcher.start()
        LOG.info('Watcher started.')

        LOG.info('(PID:%s) SensorContainer started.', os.getpid())
        sensor_container = SensorContainer(sensor_instances=sensors_to_run)
        try:
            exit_code = sensor_container.run()
            LOG.info('(PID:%s) SensorContainer stopped. Reason - run ended.', os.getpid())
            return exit_code
        except (KeyboardInterrupt, SystemExit):
            LOG.info('(PID:%s) SensorContainer stopped. Reason - %s', os.getpid(),
                     sys.exc_info()[0].__name__)
            return 0
        finally:
            self._trigger_watcher.stop()

    def _create_handler(self, trigger):
        name = trigger.type['name']
        self._trigger_names[str(trigger.id)] = trigger
        sensor = self._trigger_sensors.get(name, None)
        if sensor:
            sensor.add_trigger(SensorContainerManager.sanitize_trigger(trigger))

    def _update_handler(self, trigger):
        name = trigger.type['name']
        self._trigger_names[str(trigger.id)] = trigger
        sensor = self._trigger_sensors.get(name, None)
        if sensor:
            sensor.update_trigger(SensorContainerManager.sanitize_trigger(trigger))

    def _delete_handler(self, trigger):
        triggerid = str(trigger.id)
        if triggerid not in self._trigger_names:
            return
        del self._trigger_names[triggerid]
        name = trigger.type['name']
        sensor = self._trigger_sensors.get(name, None)
        if sensor:
            sensor.remove_trigger(SensorContainerManager.sanitize_trigger(trigger))

    def _get_config(self, sensor_path):
        sensor_dir, sensor_filename = os.path.split(sensor_path)
        config_filepath = os.path.join(sensor_dir, sensor_filename.replace('.py', '_config.json'))
        if os.path.exists(config_filepath):
            with open(config_filepath) as config_file:
                return json.load(config_file)
        else:
            return {}

    @staticmethod
    def sanitize_trigger(trigger):
        sanitized = trigger._data
        if 'id' in sanitized:
            # Friendly objectid rather than the MongoEngine representation.
            sanitized['id'] = str(sanitized['id'])
        return sanitized
