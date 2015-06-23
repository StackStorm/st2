import os
import sys

import eventlet
from oslo.config import cfg

from st2common import log as logging
from st2common.service_setup import setup as common_setup
from st2common.service_setup import teardown as common_teardown
from st2common.exceptions.sensors import SensorNotFoundException
from st2common.persistence.sensor import SensorType
from st2reactor.sensor import config
from st2common.triggers import register_internal_trigger_types
from st2reactor.container.manager import SensorContainerManager

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)


LOG = logging.getLogger('st2reactor.bin.sensors_manager')


def _setup():
    common_setup(service='sensorcontainer', config=config, setup_db=True,
                 register_mq_exchanges=True, register_signal_handlers=True)

    register_internal_trigger_types()


def _teardown():
    common_teardown()


def _get_all_sensors():
    sensors = SensorType.get_all()
    LOG.info('Found %d registered sensors in db scan.', len(sensors))
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
            if not sensors:
                raise SensorNotFoundException('Sensor %s not found in db.' % cfg.CONF.sensor_name)

        if not sensors:
            msg = 'No sensors configured to run. See http://docs.stackstorm.com/sensors.html. ' + \
                  'Register some sensors and a container will pick them to run.'
            LOG.info(msg)

        return container_manager.run_sensors(sensors=sensors)
    except SystemExit as exit_code:
        return exit_code
    except SensorNotFoundException as e:
        LOG.exception(e)
        return 1
    except:
        LOG.exception('(PID:%s) SensorContainer quit due to exception.', os.getpid())
        return 2
    finally:
        _teardown()
