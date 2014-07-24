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
from st2reactor import app
from st2reactor import config
from st2reactor.container.base import get_sensor_container
from st2reactor.container.containerservice import ContainerService
import st2reactor.container.utils as container_utils
from st2reactor.sensor.base import Sensor
from wsgiref import simple_server


LOG = logging.getLogger('st2reactor.bin.sensor_container')


def _setup():
    # setup config before anything else.
    config.parse_args()
    # 1. setup logging.
    logging.setup(cfg.CONF.reactor_logging.config_file)
    # 2. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
             cfg.CONF.database.port)


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
    return _run_sensors(sensors_dict)


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
                sensors_to_run.append(sensor)

    LOG.info('SensorContainer process[{}] started.'.format(os.getpid()))
    sensor_container = get_sensor_container(sensor_instances=sensors_to_run)
    return sensor_container.run()


def _run_server():

    host = cfg.CONF.reactor_api.host
    port = cfg.CONF.reactor_api.port

    server = simple_server.make_server(host, port, app.setup_app())

    LOG.info("Reactor API is serving on http://%s:%s (PID=%s)",
             host, port, os.getpid())

    server.serve_forever()


def main():
    _setup()
    try:
        if _is_single_sensor_mode():
            _run_sensor(cfg.CONF.sensor_path)
        else:
            sensors_dict = _load_sensor_modules(os.path.realpath(cfg.CONF.sensors.system_path))
            user_sensor_dict = _load_sensor_modules(os.path.realpath(cfg.CONF.sensors.modules_path))

            sensors_dict.update(user_sensor_dict)
            LOG.info('Found %d sensors.', len(sensors_dict))

            _run_sensors(sensors_dict)

        _run_server()
    except KeyboardInterrupt:
        LOG.info('Interrupted by user')
    finally:
        _teardown()
