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
import signal
import time
import sys

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    from st2reactor.sensor.base import Sensor
except ImportError:
    Sensor = object


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, *args, callbacks=None, **kwargs):
        self.callbacks = callbacks or {}

    def dispatch(self, event):
        if not event.is_synthetic and not event.is_directory:
            super().dispatch(event)

    def on_created(self, event):
        cb = self.callbacks.get('created')
        if cb:
            cb(event=event)

    def on_modified(self, event):
        cb = self.callbacks.get('modified')
        if cb:
            cb(event=event)

    def on_moved(self, event):
        cb = self.callbacks.get('moved')
        if cb:
            cb(event=event)

    def on_deleted(self, event):
        cb = self.callbacks.get('deleted')
        if cb:
            cb(event=event)


class SingleFileTail(object):
    def __init__(self, path, handler, read_all=False, observer=None):
        self.path = path
        self.handler = handler
        self.read_all = read_all
        self.buffer = ''
        self.observer = observer or Observer()

        self.open()

    def read(self, event=None):
        while True:
            # Buffer 1024 bytes at a time
            buff = os.read(self.fd, 1024)
            if not buff:
                return

            # Possible bug? What if the 1024 cuts off in the middle of a utf8
            # code point?
            # We use errors='replace' to have Python replace the unreadable
            # character with an "official U+FFFD REPLACEMENT CHARACTER"
            # This isn't great, but it's better than the previous behavior,
            # which blew up on any issues.
            buff = buff.decode(encoding='utf8', errors='replace')

            # An alternative is to try to read additional bytes one at a time
            # until we can decode the string properly
            # while True:
            #     try:
            #         buff = buff.decode(encoding='utf8')
            #     except UnicodeDecodeError:
            #         # Try to read another byte (this may not read anything)
            #         b = os.read(self.fd, 1)
            #         # If we read something
            #         if b:
            #             buff += b
            #         else:
            #             buff = buff.decode(encoding='utf8', errors='ignore')
            #     else:
            #         # If we could decode to UTF-8, then continue
            #         break

            # Append to previous buffer
            if self.buffer:
                buff = self.buffer + buff
                self.buffer = ''

            lines = buff.splitlines(True)
            # If the last character of the last line is not a newline
            if lines[-1][-1] != '\n':  # Incomplete line in the buffer
                self.buffer = lines[-1]  # Save the last line fragment
                lines = lines[:-1]

            for line in lines:
                self.handler(self.path, line[:-1])

    def reopen(self, event=None, skip_to_end=False):
        # stat the file on disk
        file_stat = os.stat(self.path)

        # stat the file from the existing file descriptor
        fd_stat = os.fstat(self.fd)
        # Seek right back where we thought we were
        pos = os.lseek(self.fd, 0, os.SEEK_CUR)

        # If the file now on disk is larger than where we were currently reading
        if fd_stat.st_size > pos:
            # More data to read - read as normal
            self.read()
        # If the file now on disk is smaller (eg: if the file is a freshly
        # rotated log), or if its inode has changed
        if self.stat.st_size > file_stat.st_size or \
           self.stat.st_ino != file_stat:
            self.close()
            # Since we already read the entirety of the previous file, we don't
            # want to skip any of the new file's contents, so don't seek to the
            # end, and try to read from it immediately
            self.open(seek_to_end=False)
            self.read()

    def open(self, seek_to_end=False):
        self.stat = os.stat(self.path)
        self.fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)

        if not self.read_all or seek_to_end:
            os.lseek(self.fd, 0, os.SEEK_END)

        file_event_handler = FileEventHandler(callbacks={
            'created': None,
            'modified': self.read,
            'moved': self.reopen,
            'deleted': self.reopen,
        })
        self.watch = self.observer.schedule(file_event_handler, self.path)

    def close(self):
        os.close(self.fd)
        self.observer.unschedule(self.watch)
        if self.buffer:
            self.handler(self.path, self.buffer)


class TailManager(object):
    def __init__(self, *args, **kwargs):
        self.observer = Observer()
        self.tails = {}

    def tail_file(self, path, handler, read_all=False):
        if handler not in self.tails.setdefault(path, {}):
            sft = SingleFileTail(path, handler,
                                 read_all=read_all, observer=self.observer)
            self.tails[path][handler] = sft

    def stop_tailing_file(self, path, handler):
        tailed_file = self.tails.get(path, {}).pop(handler)
        tailed_file.close()
        # Amortize some cleanup while we're at it
        if not self.tails.get(path):
            self.tails.pop(path)

    def run(self):
        self.start()
        while True:
            time.sleep(1)

    def start(self):
        self.observer.start()

    def stop(self):
        for handlers in self.tails.values():
            for tailed_file in handlers.values():
                tailed_file.close()
        self.observer.stop()
        self.observer.join()


class FileWatchSensor(Sensor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop = False
        self.trigger = None
        self.logger = self.sensor_service.get_logger(__name__)

    def setup(self):
        self.tail_manager = TailManager()

    def run(self):
        self.tail_manager.run()
        while not self._stop:
            eventlet.sleep(60)

    def cleanup(self):
        self._stop = True
        self.tail_manager.stop()

    def add_trigger(self, trigger):
        file_path = trigger['parameters'].get('file_path', None)

        if not file_path:
            self._logger.error('Received trigger type without "file_path" field.')
            return

        self.trigger = trigger.get('ref', None)

        if not self._trigger:
            raise Exception('Trigger %s did not contain a ref.' % trigger)

        self.tail_manager.tail_file(file_path, self._handle_line)
        self.logger.info('Added file "%s"' % (file_path))

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        file_path = trigger['parameters'].get('file_path', None)

        if not file_path:
            self.logger.error('Received trigger type without "file_path" field.')
            return

        self.tail_manager.stop_tailing_file(file_path, self._handle_line)
        self.trigger = None

        self.logger.info('Removed file "%s"' % (file_path))

    def _handle_line(self, file_path, line):
        payload = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'line': line
        }
        self._logger.debug('Sending payload %s for trigger %s to sensor_service.',
                           payload, self.trigger)
        self.sensor_service.dispatch(trigger=trigger, payload=payload)


if __name__ == '__main__':
    tm = TailManager()
    tm.tail_file('test.py', handler=print)
    tm.run()

    def halt(sig, frame):
        tm.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, halt)
