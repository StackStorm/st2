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
import time
import threading

from st2reactor.sensor.base import Sensor


class FileWatchSensor(Sensor):
    def __init__(self, sensor_service, config=None):
        super(FileWatchSensor, self).__init__(
            sensor_service=sensor_service, config=config
        )
        self.log = self._sensor_service.get_logger(__name__)
        self._watchers = {}  # file_path -> (thread, stop_event)
        self.file_ref = {}

    def setup(self):
        pass

    def run(self):
        while True:
            time.sleep(1)

    def cleanup(self):
        for file_path in list(self._watchers):
            self._stop_watcher(file_path)

    def add_trigger(self, trigger):
        file_path = trigger["parameters"].get("file_path", None)

        if not file_path:
            self.log.error('Received trigger type without "file_path" field.')
            return

        ref = trigger.get("ref", None)

        if not ref:
            raise Exception(f"Trigger {trigger} did not contain a ref.")

        self.file_ref[file_path] = ref

        stop_event = threading.Event()
        t = threading.Thread(
            target=self._tail, args=(file_path, stop_event), daemon=True
        )
        self._watchers[file_path] = (t, stop_event)
        t.start()

        self.log.info(f"Added file '{file_path}' ({ref}) to watch list.")

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        file_path = trigger["parameters"].get("file_path", None)

        if not file_path:
            self.log.error("Received trigger type without 'file_path' field.")
            return

        self._stop_watcher(file_path)
        self.file_ref.pop(file_path, None)

        self.log.info(f"Removed file '{file_path}' from watch list.")

    def _stop_watcher(self, file_path):
        if file_path in self._watchers:
            _, stop_event = self._watchers.pop(file_path)
            stop_event.set()

    def _tail(self, file_path, stop_event):
        with open(file_path, "r") as f:
            f.seek(0, 2)  # seek to EOF
            while not stop_event.is_set():
                line = f.readline()
                if line:
                    self._handle_line(file_path, line.strip())
                else:
                    time.sleep(0.1)

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
