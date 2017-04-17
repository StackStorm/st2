import os

from logshipper.tail import Tail

from st2reactor.sensor.base import Sensor


class FileWatchSensor(Sensor):
    def __init__(self, sensor_service, config=None):
        super(FileWatchSensor, self).__init__(sensor_service=sensor_service,
                                              config=config)
        self._trigger_ref = 'linux.file_watch.line'
        self._logger = self._sensor_service.get_logger(__name__)

        self._file_paths = []  # stores a list of file paths we are monitoring
        self._tail = None

    def setup(self):
        self._tail = Tail(filenames=[])
        self._tail.handler = self._handle_line
        self._tail.should_run = True

    def run(self):
        self._tail.run()

    def cleanup(self):
        if self._tail:
            self._tail.should_run = False

            try:
                self._tail.notifier.stop()
            except Exception:
                pass

    def add_trigger(self, trigger):
        if trigger['type'] not in ['linux.file_watch.file_path']:
            return

        file_path = trigger['parameters']['file_path']
        self._tail.add_file(filename=file_path)

        self._logger.info('Added file "%s"' % (file_path))

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        if trigger['type'] not in ['linux.file_watch.file_path']:
            return

        file_path = trigger['parameters']['file_path']
        self._tail.remove_file(filename=file_path)

        self._logger.info('Removed file "%s"' % (file_path))

    def _handle_line(self, file_path, line):
        trigger = self._trigger_ref
        payload = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'line': line
        }
        self.sensor_service.dispatch(trigger=trigger, payload=payload)
