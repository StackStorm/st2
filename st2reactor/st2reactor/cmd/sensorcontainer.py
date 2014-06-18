from st2reactor import config

from collections import defaultdict
import fnmatch
import os
import re

from oslo.config import cfg
from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
import st2common.util.loader as sensors_loader
from st2reactor.container.base import SensorContainer
from st2reactor.container.containerservice import ContainerService
import st2reactor.container.utils as container_utils
from st2reactor.sensor.base import Sensor


LOG = logging.getLogger('st2reactor.bin.sensor_container')


def __load_sensor_modules():
    path = os.path.realpath(cfg.CONF.sensors.modules_path)
    '''
    XXX: For now, let's just hardcode the includes pattern
    here. We should eventually move these to config if that makes sense
    at all.
    '''
    includes = ['*.py']

    # transform glob patterns to regular expressions
    includes = r'|'.join([fnmatch.translate(x) for x in includes])

    if not os.path.isdir(path):
        raise Exception('Directory containing sensors must be provided.')

    LOG.info('Loading sensor modules from path: %s' % path)

    plugins = []
    for (dirpath, dirnames, filenames) in os.walk(path):
        # exclude/include files
        files = [os.path.join(dirpath, f) for f in filenames]
        files = [f for f in files if re.match(includes, f)]
        plugins.extend(files)
        break
    LOG.info('Found %d sensor modules in path.' % len(plugins))

    plugins_dict = defaultdict(list)
    for plugin in plugins:
        file_path = os.path.join(path, plugin)
        try:
            plugins_dict[plugin].extend(sensors_loader.register_plugin(Sensor, file_path))
        except Exception, e:
            LOG.exception(e)
            LOG.warning('Exception registering plugin %s.' % file_path)
    return plugins_dict


def __setup():
    # setup config before anything else.
    config.parse_args()
    # 1. setup logging.
    logging.setup(cfg.CONF.reactor_logging.config_file)
    # 2. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
             cfg.CONF.database.port)


def __teardown():
    db_teardown()


def main():
    __setup()
    sensors_dict = __load_sensor_modules()
    container_service = ContainerService()
    sensors_to_run = []
    for filename, sensors in sensors_dict.iteritems():
        for sensor_class in sensors:
            try:
                sensor = sensor_class(container_service)
            except Exception, e:
                LOG.exception(e)
                LOG.warning('Unable to create instance for sensor %s in file %s' %
                            (sensor_class, filename))
                continue
            else:
                try:
                    container_utils.add_trigger_types(sensor.get_trigger_types())
                except Exception, e:
                    LOG.exception(e)
                    LOG.warning('Unable to register trigger type for sensor %s in file %s' %
                                (sensor_class, filename))
                    continue
                else:
                    sensors_to_run.append(sensor)

    LOG.info('SensorContainer process[{}] started.'.format(os.getpid()))
    sensor_container = SensorContainer(sensor_instances=sensors_to_run)
    exit_code = sensor_container.main()
    LOG.info('SensorContainer process[{}] exit with code {}.'.format(
        os.getpid(), exit_code))
    __teardown()
    return exit_code
