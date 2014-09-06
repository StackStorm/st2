from collections import defaultdict
import fnmatch
import os
import re

from st2common import log as logging
from st2common.exceptions.plugins import IncompatiblePluginException
import st2common.util.loader as sensors_loader
from st2reactor.sensor.base import Sensor

LOG = logging.getLogger('st2reactor.bin.sensor_container')


class SensorLoader(object):
    # XXX: For now, let's just hardcode the includes & excludes pattern
    # here. We should eventually move these to config if that makes sense
    # at all.
    includes = ['*.py']
    excludes = ['*/__init__.py']
    # transform glob patterns to regular expressions
    _includes = r'|'.join([fnmatch.translate(x) for x in includes])
    _excludes = r'|'.join([fnmatch.translate(x) for x in excludes])

    def _get_sensor_files(self, base_dir):
        if not os.path.isdir(base_dir):
            raise Exception('Directory containing sensors must be provided.')
        sensor_files = []
        for (dirpath, dirnames, filenames) in os.walk(base_dir):
            # exclude/include files
            files = [os.path.join(dirpath, f) for f in filenames]
            files = [f for f in files if re.match(self._includes, f)]
            files = [f for f in files if not re.match(self._excludes, f)]
            sensor_files.extend(files)
            break
        return sensor_files

    def _load_sensor(self, sensor_file_path):
        return sensors_loader.register_plugin(Sensor, sensor_file_path)

    def _get_sensor_classes(self, sensor_file_path):
        try:
            LOG.info('Loading sensors from file %s.', sensor_file_path)
            klasses = self._load_sensor(sensor_file_path)
            if klasses is not None:
                return klasses
            else:
                LOG.info('No sensors in file %s.', sensor_file_path)
        except IncompatiblePluginException as e:
            LOG.warning('Incompatible sensor: %s. Exception: %s',
                        sensor_file_path, e, exc_info=True)
        except Exception as e:
            LOG.warning('Exception loading sensor from file: %s. Exception: %s',
                        sensor_file_path, e, exc_info=True)
        return None

    def _get_sensors_from_dir(self, base_dir):
        LOG.info('Registering sensor modules from path: %s', base_dir)
        sensor_files = self._get_sensor_files(base_dir)
        LOG.info('Found %d sensor modules in path.', len(sensor_files))

        sensors_dict = defaultdict(list)
        for sensor_file in sensor_files:
            sensor_file = os.path.join(base_dir, sensor_file)
            klasses = self._get_sensor_classes(sensor_file)
            if klasses is not None:
                sensors_dict[sensor_file] = klasses
        return sensors_dict

    def get_sensors(self, base_dir=None, fil=None):
        if not base_dir and not fil:
            return None
        if base_dir:
            return self._get_sensors_from_dir(base_dir)
        if fil:
            return {fil: self._get_sensor_classes(fil)}
