import os
from oslo.config import cfg

from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2reactor.sensor import config
from st2common.persistence.reactor import SensorType
from st2reactor.container.manager import SensorContainerManager

LOG = logging.getLogger('st2reactor.bin.sensors_manager')


def _setup():
    # 1. parse config args
    config.parse_args()

    # 2. setup logging.
    logging.setup(cfg.CONF.sensorcontainer.logging)

    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
    password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
             username=username, password=password)


def _teardown():
    db_teardown()


def _get_all_sensors():
    sensors = SensorType.get_all()
    LOG.info('Found %d sensors.', len(sensors))
    return sensors


def main():
    try:
        _setup()
        container_manager = SensorContainerManager()
        sensors = _get_all_sensors()

        if cfg.CONF.sensor_name:
            # Only run a single sensor
            sensors = [sensor for sensor in sensors if
                       sensor.name == cfg.CONF.sensor_name]
        return container_manager.run_sensors(sensors=sensors)
    except:
        LOG.exception('(PID:%s) SensorContainer quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
