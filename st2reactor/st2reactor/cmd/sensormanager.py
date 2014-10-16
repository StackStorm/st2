from collections import defaultdict
import os
import sys

from oslo.config import cfg
import six

from st2common import log as logging
from st2common.content.loader import ContentPackLoader
from st2common.content.requirementsvalidator import RequirementsValidator
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2reactor import config
from st2reactor.sensor.loader import SensorLoader
from st2reactor.container.manager import SensorContainerManager

LOG = logging.getLogger('st2reactor.bin.sensors_manager')


def _setup():
    # 1. parse config args
    config.parse_args()

    # 2. setup logging.
    logging.setup(cfg.CONF.reactor.logging)

    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host,
             cfg.CONF.database.port)


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


def _is_requirements_ok(sensor_dir):
    rqmnts_file = os.path.join(sensor_dir, 'requirements.txt')

    if not os.path.exists(rqmnts_file):
        return True

    missing = RequirementsValidator.validate(rqmnts_file)
    if missing:
        LOG.warning('Sensors in %s missing dependencies: %s', sensor_dir, ','.join(missing))
        return False
    return True


def _get_user_sensors():
    sensors_dict = defaultdict(list)
    pack_loader = ContentPackLoader()
    sensor_loader = SensorLoader()
    packs = pack_loader.get_content(base_dir=cfg.CONF.content.content_packs_base_path,
                                    content_type='sensors')
    for pack, sensor_dir in six.iteritems(packs):
        try:
            LOG.info('Loading sensors from pack: %s, dir: %s', pack, sensor_dir)
            if _is_requirements_ok(sensor_dir):
                base_dir = os.path.realpath(sensor_dir)
                pack_sensors = sensor_loader.get_sensors(base_dir=base_dir)

                # Include content pack name on the sensor class
                # TODO: This is nasty
                pack_sensors_augmented = defaultdict(list)
                for filename, sensors in pack_sensors.iteritems():
                    for sensor in sensors:
                        sensor.content_pack = pack
                        pack_sensors_augmented[filename].append(sensor)

                sensors_dict.update(pack_sensors_augmented)
            else:
                LOG.warning('Not registering sensors in sensor_dir: %s.', sensor_dir)
        except:
            LOG.exception('Failed loading sensors from dir: %s' % sensor_dir)
    return sensors_dict


def _get_all_sensors():
    sensor_loader = SensorLoader()
    if _is_single_sensor_mode():
        sensors_dict = sensor_loader.get_sensors(fil=cfg.CONF.sensor_path)
    else:
        sensors_dict = sensor_loader.get_sensors(base_dir=os.path.realpath(
                                                 cfg.CONF.content.system_path))
        user_sensor_dict = _get_user_sensors()
        sensors_dict.update(user_sensor_dict)
        LOG.info('Found %d user sensors.', len(user_sensor_dict))
    return sensors_dict


def main():
    try:
        _setup()
        container_manager = SensorContainerManager()
        return container_manager.run_sensors(_get_all_sensors())
    except:
        LOG.exception('(PID:%s) SensorContainer quit due to exception.', os.getpid())
        return 1
    finally:
        _teardown()
