from st2reactor import config

import fnmatch
import os
import re

from oslo.config import cfg
from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
import st2common.util.loader as sensors_loader
from st2reactor.container.base import SensorContainer
from st2reactor.sensor.base import Sensor
from st2reactor.sensor.samples.demo import FixedRunSensor, \
    DummyTriggerGeneratorSensor


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

    plugin_instances = []
    for plugin in plugins:
        file_path = os.path.join(path, plugin)
        try:
            plugin_instances.extend(sensors_loader.register_plugin(Sensor, file_path))
        except Exception, e:
            LOG.exception(e)
            LOG.warn('Exception registering plugin %s.' % file_path)
    return plugin_instances


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
    plugin_instances = __load_sensor_modules()
    LOG.info('SensorContainer process[{}] started.'.format(os.getpid()))
    sensor_container = SensorContainer(plugin_instances)
    exit_code = sensor_container.main()
    LOG.info('SensorContainer process[{}] exit with code {}.'.format(
        os.getpid(), exit_code))
    __teardown()
    return exit_code

