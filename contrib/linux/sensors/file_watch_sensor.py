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
        self.log = self._sensor_service.get_logger(__name__)
        self.tail = None
        self.file_ref = {}

    def setup(self):
        self.tail = Tail(filenames=[])
        self.tail.handler = self._handle_line
        self.tail.should_run = True

    def run(self):
        self.tail.run()

    def cleanup(self):
        if self.tail:
            self.tail.should_run = False

            try:
                self.tail.notifier.stop()
            except Exception:
                self.log.exception("Unable to stop the tail notifier")

    def add_trigger(self, trigger):
        file_path = trigger["parameters"].get("file_path", None)

        if not file_path:
            self.log.error('Received trigger type without "file_path" field.')
            return

        trigger = trigger.get("ref", None)

        if not trigger:
            raise Exception(f"Trigger {trigger} did not contain a ref.")

        # Wait a bit to avoid initialization race in logshipper library
        eventlet.sleep(1.0)

        self.tail.add_file(filename=file_path)
        self.file_ref[file_path] = trigger

        self.log.info(f"Added file '{file_path}' ({trigger}) to watch list.")

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        file_path = trigger["parameters"].get("file_path", None)

        if not file_path:
            self.log.error("Received trigger type without 'file_path' field.")
            return

        self.tail.remove_file(filename=file_path)
        self.file_ref.pop(file_path)

        self.log.info(f"Removed file '{file_path}' ({trigger}) from watch list.")

    def _handle_line(self, file_path, line):
        if file_path not in self.file_ref:
            self.log.error(
                f"No reference found for {file_path}, unable to emit trigger!"
            )
            return

        trigger = self.file_ref[file_path]
        payload = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "line": line,
        }
        self.log.debug(
            f"Sending payload {payload} for trigger {trigger} to sensor_service."
        )
        self.sensor_service.dispatch(trigger=trigger, payload=payload)
