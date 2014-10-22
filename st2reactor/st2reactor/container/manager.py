import os
import sys
import six

from st2common import log as logging
from st2common.exceptions.sensors import TriggerTypeRegistrationException
from st2common.persistence.reactor import Trigger
from st2common.util.config_parser import ContentPackConfigParser
from st2common.content.validators import validate_content_pack_name
from st2common.constants.content_pack import SYSTEM_PACK_NAME
from st2reactor.container.base import SensorContainer
from st2reactor.container.service import ContainerService
from st2reactor.container.triggerwatcher import TriggerWatcher
import st2reactor.container.utils as container_utils

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
        # TODO: Once the API registration is in place, query DB for available
        # sensors here
        # TODO: Use trigger_types and description from sensors metadata
        for filename, sensors in six.iteritems(sensors_dict):
            for sensor_class in sensors:
                sensor_class_kwargs = {}
                class_name = sensor_class.__name__

                # System sensors which are not located inside a content pack
                # don't and can't have custom config associated with them
                content_pack = getattr(sensor_class, 'content_pack', None)
                if content_pack:
                    # TODO: Don't parse the same config multiple times when we
                    # are referring to sensors from the same pack
                    content_pack = validate_content_pack_name(name=content_pack)
                    config_parser = ContentPackConfigParser(content_pack_name=content_pack)
                    config = config_parser.get_sensor_config(sensor_file_path=filename)

                    if config:
                        sensor_class_kwargs['config'] = config.config
                        LOG.info('Using config "%s" for sensor "%s"' % (config.file_path,
                                                                        class_name))
                    else:
                        LOG.info('No config found for sensor "%s"' % (class_name))
                        sensor_class_kwargs['config'] = {}
                else:
                    content_pack = SYSTEM_PACK_NAME

                try:
                    sensor = sensor_class(container_service=container_service,
                                          **sensor_class_kwargs)
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
                        assert isinstance(trigger_types, (list, tuple))
                        trigger_type_dbs = container_utils.add_trigger_models(
                            content_pack=content_pack,
                            trigger_types=trigger_types)
                except TriggerTypeRegistrationException as e:
                    LOG.warning('Unable to register trigger type for sensor %s in file %s.'
                                + ' Exception: %s', sensor_class, filename, e, exc_info=True)
                    continue

                # Populate sensors dict
                trigger_type_refs = []
                for trigger_type_db, _ in trigger_type_dbs:
                    ref_obj = trigger_type_db.get_reference()
                    trigger_type_ref = ref_obj.ref
                    self._trigger_sensors[trigger_type_ref] = sensor
                    trigger_type_refs.append(trigger_type_ref)

                # Register sensor type in the DB
                sensor_obj = {
                    'filename': os.path.abspath(filename),
                    'name': class_name,
                    'class_name': class_name,
                    'trigger_types': trigger_type_refs
                }
                container_utils.add_sensor_model(content_pack=content_pack,
                                                 sensor=sensor_obj)

                # Add good sensor to the run list
                sensors_to_run.append(sensor)

        for trigger in Trigger.get_all():
            self._create_handler(trigger=trigger)

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
        trigger_type_ref = trigger.type
        self._trigger_names[str(trigger.id)] = trigger
        sensor = self._trigger_sensors.get(trigger_type_ref, None)
        if sensor:
            sensor.add_trigger(SensorContainerManager.sanitize_trigger(trigger))

    def _update_handler(self, trigger):
        trigger_type_ref = trigger.type
        self._trigger_names[str(trigger.id)] = trigger
        sensor = self._trigger_sensors.get(trigger_type_ref, None)
        if sensor:
            sensor.update_trigger(SensorContainerManager.sanitize_trigger(trigger))

    def _delete_handler(self, trigger):
        triggerid = str(trigger.id)
        if triggerid not in self._trigger_names:
            return
        del self._trigger_names[triggerid]
        trigger_type_ref = trigger.type
        sensor = self._trigger_sensors.get(trigger_type_ref, None)
        if sensor:
            sensor.remove_trigger(SensorContainerManager.sanitize_trigger(trigger))

    @staticmethod
    def sanitize_trigger(trigger):
        sanitized = trigger._data
        if 'id' in sanitized:
            # Friendly objectid rather than the MongoEngine representation.
            sanitized['id'] = str(sanitized['id'])
        return sanitized
