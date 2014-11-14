import os
import sys

from oslo.config import cfg

from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2reactor import config
from st2common.persistence.reactor import SensorType
from st2reactor.container.manager import SensorContainerManager

LOG = logging.getLogger('st2reactor.bin.sensors_manager')


def _setup():
    # 1. parse config args
    config.parse_args()

    # 2. setup logging.
    logging.setup(cfg.CONF.reactor.logging)

    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
    password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
             username=username, password=password)


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


def _get_all_sensors():
    sensors = SensorType.get_all()
    LOG.info('Found %d sensors.', len(sensors))
    return sensors


def main():
    try:
        _setup()
        container_manager = SensorContainerManager()
        sensors = _get_all_sensors()
        return container_manager.run_sensors(sensors=sensors)
    except:
        LOG.exception('(PID:%s) SensorContainer quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
