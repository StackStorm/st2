# Copyright 2014 Koert van der Veer
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


import logging
import os

import six
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


LOG = logging.getLogger(__name__)


class FileTail(object):
    __slots__ = ['file_descriptor', 'path', 'recursive', 'watch', 'buffer']

    def __init__(self, file_descriptor=None, recursive=None, path=None,
                 watch=None, buffer=None):
        if buffer is None:
            self.buffer = b""
        else:
            self.buffer = buffer
        self.file_descriptor = file_descriptor
        self.recursive = recursive
        self.path = path
        self.watch = watch


class Tail(FileSystemEventHandler):
    """Follows files, and processes new lines in those files with a callback
    handler.

    Directories are supported, and new files matching the wildcard will be
    discovered.

    Rotated files are automatically discovered, and reopened.

    Example for ``input.yml``:

    .. code:: yaml

        - tail:
            filename:
            - /var/log/syslog
            - /var/log/my_app/*.log
    """
    log = None

    def __init__(self, handler=None, filenames=None, log=LOG, *args, **kwargs):
        # pylint: disable=no-member
        self.handler = handler

        if isinstance(filenames, six.string_types):
            filenames = [filenames]

        self.tails = {}
        self.log = log
        self.observer = Observer()

        if filenames:
            for filename in filenames:
                self.add_file(filename)

    def set_handler(self, handler):
        self.handler = handler

    def add_file(self, filepath, recursive=True, seek_to_end=True):
        self.log.debug("adding tail %s", filepath)
        if os.path.isdir(filepath):
            seek_to_end = False
        else:
            recursive = False
        self.tails[filepath] = self.open_tail(filepath, recursive, seek_to_end)

    def remove_file(self, filepath):
        self.log.debug("removing tail %s", filepath)
        tail = self.tails.get(filepath)
        if tail is not None:
            self.close_tail(tail)

    def remove_tails(self):
        self.log.debug("remove tails")

        for filepath in self.tails.keys():
            self.remove_file(filepath)

    def start(self):
        self.log.debug("starting tails")
        self.run()

    def stop(self):
        self.log.debug("stopping tails")
        self.remove_tails()

    def run(self):
        self.observer.start()

    def on_modified(self, event):
        self.log.info("%s modified. processing")
        self.process_tail(event.src_path)

    def on_moved(self, event):
        self.log.info("%s looks rotated. reopening", event.src_path)
        tail = self.tails.get(event.src_path)
        if tail:
            self.log.info("closing (old) rotated file")
            self.close_tail(tail)
        self.log.info("opening (new) rotated file")
        self.reprocess_tail(event.src_path, event.dest_path)

    def process_tail(self, path, seek_to_end=False):
        # pylint: disable=no-member
        self.log.debug("process_tail for %s", path)
        # Find or create a tail.
        tail = self.tails.get(path)
        if tail:
            fd_stat = os.fstat(tail.file_descriptor)
            pos = os.lseek(tail.file_descriptor, 0, os.SEEK_CUR)
            if fd_stat.st_size > pos:
                self.log.debug("something to read")
                self.read_tail(tail)
            elif fd_stat.st_size < pos:
                self.log.debug("file shrunk, seeking to new end")
                os.lseek(tail.file_descriptor, 0, os.SEEK_END)
        else:
            self.log.info("tailing %s", path)
            self.tails[path] = tail = self.open_tail(path, seek_to_end=seek_to_end)

    def reprocess_tail(self, src_path, dest_path):
        self.log.debug("reprocess_tail for %s moved to %s", src_path, dest_path)
        # pylint: disable=no-member

        # Find or create a tail.
        tail = self.tails.get(dest_path)
        if not tail:
            self.log.info("tailing %s", dest_path)
            self.tails[dest_path] = tail = self.open_tail(dest_path)

    def read_tail(self, tail):
        self.log.debug("reading tail %s", tail.path)
        while True:
            buff = os.read(tail.file_descriptor, 1024)
            if not buff:
                return

            buff = buff.decode('utf8')

            # Append to last buffer
            if tail.buffer:
                buff = tail.buffer + buff
                tail.buffer = ""

            lines = buff.splitlines(True)
            if lines[-1][-1] != "\n":  # incomplete line in buffer
                # Save the remainder of the last line as the buffer
                # This fixes a bug in the original logshipper.Tail
                # implementation, which only assigned the last character:
                # tail.buffer = lines[-1][-1]
                # The last [-1] was unnecessary
                tail.buffer = lines[-1]
                # Only return lines with newlines
                lines = lines[:-1]

            for line in lines:
                self.handler(file_path=tail.path, line=line[:-1])

    def open_tail(self, path, recursive=True, seek_to_end=False):
        self.log.info("Opening tail %s", path)
        # pylint: disable=no-member
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        watch = self.observer.schedule(self, path, recursive)
        tail = FileTail(file_descriptor=fd, path=path, recursive=recursive,
                        watch=watch)

        if seek_to_end:
            os.lseek(tail.file_descriptor, 0, os.SEEK_END)

        return tail

    def close_tail(self, tail):
        # pylint: disable=no-member
        self.log.info("Closing tail %s", tail.path)
        try:
            self.observer.unschedule(tail.watch)
        except KeyError:
            pass
        try:
            os.close(tail.file_descriptor)
        except OSError:
            pass
        self.observer.stop()
        self.observer.join()
        if tail.buffer:
            self.log.debug("triggering from tail buffer")
            self.handler(file_path=tail.path, line=tail.buffer)
            # Empty out tail.buffer so closing the same tail multiple times
            # doesn't dispatch multiple times
            tail.buffer = ""
