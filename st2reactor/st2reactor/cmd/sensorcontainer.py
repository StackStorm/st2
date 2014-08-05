from collections import defaultdict
import fnmatch
import os
import re
import sys

from oslo.config import cfg
from st2common import log as logging
from st2common.exceptions.plugins import IncompatiblePluginException
from st2common.exceptions.sensors import TriggerTypeRegistrationException
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
import st2common.util.loader as sensors_loader
from st2reactor import config
from st2reactor.container.base import SensorContainer
from st2reactor.container.containerservice import ContainerService
import st2reactor.container.utils as container_utils
from st2reactor.sensor.base import Sensor


LOG = logging.getLogger('st2reactor.bin.sensor_container')


def _setup():
    # 1. parse config args
    config.parse_args()

    # 2. setup logging.
    logging.setup(cfg.CONF.reactor_logging.config_file)

    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
             cfg.CONF.database.port)

    # 4. ensure paths exist
    if not os.path.exists(cfg.CONF.sensors.modules_path):
        os.makedirs(cfg.CONF.sensors.modules_path)


def _teardown():
    db_teardown()


def _load_sensor(sensor_file_path):
    return sensors_loader.register_plugin(Sensor, sensor_file_path)


def _load_sensor_modules(path):
    '''
    XXX: For now, let's just hardcode the includes & excludes pattern
    here. We should eventually move these to config if that makes sense
    at all.
    '''
    includes = ['*.py']
    excludes = ['*/__init__.py']

    # transform glob patterns to regular expressions
    includes = r'|'.join([fnmatch.translate(x) for x in includes])
    excludes = r'|'.join([fnmatch.translate(x) for x in excludes])

    if not os.path.isdir(path):
        raise Exception('Directory containing sensors must be provided.')

    LOG.info('Loading sensor modules from path: %s', path)

    plugins = []
    for (dirpath, dirnames, filenames) in os.walk(path):
        # exclude/include files
        files = [os.path.join(dirpath, f) for f in filenames]
        files = [f for f in files if re.match(includes, f)]
        files = [f for f in files if not re.match(excludes, f)]
        plugins.extend(files)
        break
    LOG.info('Found %d sensor modules in path.', len(plugins))

    plugins_dict = defaultdict(list)
    for plugin in plugins:
        file_path = os.path.join(path, plugin)
        try:
            LOG.info('Loading sensors from file %s.', file_path)
            klasses = _load_sensor(file_path)
            if klasses is not None:
                plugins_dict[plugin].extend(klasses)
            else:
                LOG.info('No sensors in file %s.', file_path)

        except IncompatiblePluginException as e:
            LOG.warning('Incompatible sensor: %s. Exception: %s', file_path, e, exc_info=True)
        except Exception as e:
            LOG.warning('Exception loading sensor from file: %s. Exception: %s', file_path, e,
                        exc_info=True)
    return plugins_dict


def _is_single_sensor_mode():
    if cfg.CONF.sensor_path is not None:
        LOG.info('Running in sensor testing mode.')
        sensor_to_test = cfg.CONF.sensor_path
        if not os.path.exists(sensor_to_test):
            LOG.error('Unable to find sensor file %s', sensor_to_test)
            sys.exit(-1)
        else:
            return True


def _run_sensor(sensor_file_path):
    sensors_dict = defaultdict(list)
    try:
        sensors_dict[sensor_file_path].extend(_load_sensor(sensor_file_path))
    except IncompatiblePluginException as e:
        LOG.warning('Exception registering plugin %s. Exception: %s', sensor_file_path, e,
                    exc_info=True)
        return -1
    exit_code = _run_sensors(sensors_dict)
    LOG.info('SensorContainer process[{}] exit with code {}.'.format(
        os.getpid(), exit_code))
    _teardown()
    return exit_code


def _run_sensors(sensors_dict):
    LOG.info('Setting up container to run %d sensors.', len(sensors_dict))
    container_service = ContainerService()
    sensors_to_run = []
    for filename, sensors in sensors_dict.iteritems():
        for sensor_class in sensors:
            try:
                sensor = sensor_class(container_service)
            except Exception as e:
                LOG.warning('Unable to create instance for sensor %s in file %s. Exception: %s',
                            sensor_class, filename, e, exc_info=True)
                continue
            else:
                try:
                    trigger_type = sensor.get_trigger_types()
                    if not trigger_type:
                        LOG.warning('No trigger type registered by sensor %s in file %s',
                                    sensor_class, filename)
                    else:
                        container_utils.add_trigger_types(sensor.get_trigger_types())
                except TriggerTypeRegistrationException as e:
                    LOG.warning('Unable to register trigger type for sensor %s in file %s.'
                                + ' Exception: %s', sensor_class, filename, e, exc_info=True)
                    continue
                else:
                    sensors_to_run.append(sensor)

    LOG.info('SensorContainer process[{}] started.'.format(os.getpid()))
    sensor_container = SensorContainer(sensor_instances=sensors_to_run)
    return sensor_container.run()


def main():
    _setup()
    sensors_dict = None
    if _is_single_sensor_mode():
        return _run_sensor(cfg.CONF.sensor_path)
    else:
        sensors_dict = _load_sensor_modules(os.path.realpath(cfg.CONF.sensors.system_path))
        user_sensor_dict = _load_sensor_modules(os.path.realpath(cfg.CONF.sensors.modules_path))
        sensors_dict.update(user_sensor_dict)
        LOG.info('Found %d sensors.', len(sensors_dict))
        exit_code = _run_sensors(sensors_dict)
        _teardown()
        LOG.info('SensorContainer process[{}] exit with code {}.'.format(
            os.getpid(), exit_code))
        return exit_code
