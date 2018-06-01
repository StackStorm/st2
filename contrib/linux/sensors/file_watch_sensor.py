import os

from tail import Tail

from st2reactor.sensor.base import Sensor


class FileWatchSensor(Sensor):
    def __init__(self, sensor_service, config=None):
        super(FileWatchSensor, self).__init__(sensor_service=sensor_service,
                                              config=config)
        self._trigger = None
        self._logger = self._sensor_service.get_logger(__name__)
        self._tail = None

    def setup(self):
        self._tail = Tail(filenames=[])
        self._tail.set_handler(self._handle_line)

    def run(self):
        self._tail.start()

    def cleanup(self):
        if self._tail:
            try:
                self._tail.stop()
            except Exception:
                pass

    def add_trigger(self, trigger):
        file_path = trigger['parameters'].get('file_path', None)

        if not file_path:
            self._logger.error('Received trigger type without "file_path" field.')
            return

        self._trigger = trigger.get('ref', None)

        if not self._trigger:
            raise Exception('Trigger %s did not contain a ref.' % trigger)

        self._tail.add_file(filepath=file_path)
        self._logger.info('Added file "%s"' % (file_path))

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        file_path = trigger['parameters'].get('file_path', None)

        if not file_path:
            self._logger.error('Received trigger type without "file_path" field.')
            return

        self._tail.remove_file(filepath=file_path)
        self._trigger = None

        self._logger.info('Removed file "%s"' % (file_path))

    def _handle_line(self, file_path, line):
        trigger = self._trigger
        payload = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'line': line
        }
        self._logger.debug('Sending payload %s for trigger %s to sensor_service.',
                           payload, trigger)
        self.sensor_service.dispatch(trigger=trigger, payload=payload)
