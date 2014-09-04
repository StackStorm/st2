from collections import defaultdict
import os
import sys

from oslo.config import cfg

from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2reactor import config
from st2reactor.sensor.loader import SensorLoader
from st2reactor.container.containermanager import SensorContainerManager

LOG = logging.getLogger('st2reactor.bin.sensors_manager')


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


def _is_single_sensor_mode():
    sensor_to_test = cfg.CONF.sensor_path

    if sensor_to_test is not None:
        LOG.info('Running in sensor testing mode.')
        if not os.path.exists(sensor_to_test):
            LOG.error('Unable to find sensor file %s', sensor_to_test)
            sys.exit(-1)
        else:
            return True


def main():
    _setup()
    sensor_loader = SensorLoader()
    sensors_dict = defaultdict(list)
    container_manager = SensorContainerManager()
    if _is_single_sensor_mode():
        sensors_dict = sensor_loader.get_sensors(fil=cfg.CONF.sensor_path)
    else:
        sensors_dict = sensor_loader.get_sensors(base_dir=os.path.realpath(
                                                 cfg.CONF.sensors.system_path))
        user_sensor_dict = sensor_loader.get_sensors(base_dir=os.path.realpath(
                                                     cfg.CONF.sensors.modules_path))
        sensors_dict.update(user_sensor_dict)
        LOG.info('Found %d user sensors.', len(user_sensor_dict))
    exit_code = container_manager.run_sensors(sensors_dict)
    _teardown()
    return exit_code
