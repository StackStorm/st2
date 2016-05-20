import os

from logshipper.tail import Tail

from st2reactor.sensor.base import Sensor


class FileWatchSensor(Sensor):
    def __init__(self, sensor_service, config=None):
        super(FileWatchSensor, self).__init__(sensor_service=sensor_service,
                                              config=config)
        self._config = self._config['file_watch_sensor']

        self._file_paths = self._config.get('file_paths', [])
        self._trigger_ref = 'linux.file_watch.line'
        self._tail = None

    def setup(self):
        if not self._file_paths:
            raise ValueError('No file_paths configured to monitor')

        self._tail = Tail(filenames=self._file_paths)
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
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass

    def _handle_line(self, file_path, line):
        trigger = self._trigger_ref
        payload = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'line': line
        }
        self.sensor_service.dispatch(trigger=trigger, payload=payload)
