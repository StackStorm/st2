# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import eventlet

from logshipper.tail import Tail

from st2reactor.sensor.base import Sensor


class FileWatchSensor(Sensor):
    def __init__(self, sensor_service, config=None):
        super(FileWatchSensor, self).__init__(
            sensor_service=sensor_service, config=config
        )
        self._trigger = None
        self._logger = self._sensor_service.get_logger(__name__)
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
                self._logger.exception("Unable to stop the tail notifier")

    def add_trigger(self, trigger):
        file_path = trigger["parameters"].get("file_path", None)

        if not file_path:
            self._logger.error('Received trigger type without "file_path" field.')
            return

        self._trigger = trigger.get("ref", None)

        if not self._trigger:
            raise Exception("Trigger %s did not contain a ref." % trigger)

        # Wait a bit to avoid initialization race in logshipper library
        eventlet.sleep(1.0)

        self._tail.add_file(filename=file_path)
        self._logger.info('Added file "%s"' % (file_path))

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        file_path = trigger["parameters"].get("file_path", None)

        if not file_path:
            self._logger.error('Received trigger type without "file_path" field.')
            return

        self._tail.remove_file(filename=file_path)
        self._trigger = None

        self._logger.info('Removed file "%s"' % (file_path))

    def _handle_line(self, file_path, line):
        trigger = self._trigger
        payload = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "line": line,
        }
        self._logger.debug(
            "Sending payload %s for trigger %s to sensor_service.", payload, trigger
        )
        self.sensor_service.dispatch(trigger=trigger, payload=payload)
