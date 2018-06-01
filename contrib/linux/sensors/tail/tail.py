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


import glob
import logging

import eventlet
from eventlet.green import os
import inotify.adapters
import inotify.constants as in_constants
import six

LOG = logging.getLogger(__name__)

INOTIFY_FILE_MASK = (in_constants.IN_MODIFY | in_constants.IN_OPEN)
INOTIFY_DIR_MASK = (in_constants.IN_CREATE | in_constants.IN_DELETE | in_constants.IN_MOVE)


class BaseInput(object):
    handler = None
    should_run = False
    thread = None

    def set_handler(self, handler):
        self.handler = handler

    def start(self):
        LOG.debug("starting: should_run %r", self.should_run)
        self.should_run = True
        if self.thread is None:
            self.thread = eventlet.spawn(self._run)
        return self.thread

    def stop(self):
        LOG.debug("stopping: should_run %r", self.should_run)
        self.should_run = False
        thread = self.thread
        if thread is not None:
            thread.wait()
        self.thread = None

    def _run(self):
        try:
            self.run()
        except Exception as e:
            LOG.exception("Encountered exception while running %s", self)
            raise e

    def run(self):
        raise NotImplementedError  # pragma: no cover


class Tail(BaseInput):
    """Follows files, and processes new lines in those files with a callback
    handler.

    Glob-style wildcards are supported, and new files matching the wildcard
    will be discovered.

    Rotated files are automatically discovered, and reopened.

    Example for ``input.yml``:

    .. code:: yaml

        - tail:
            filename:
            - /var/log/syslog
            - /var/log/my_app/*.log
    """

    class FileTail(object):
        __slots__ = ['file_descriptor', 'path', 'buffer', 'stat', 'rescan',
                     'watch_descriptor']

        def __init__(self):
            self.buffer = b""
            self.file_descriptor = None
            self.path = None
            self.rescan = None
            self.stat = None
            self.watch_descriptor = None

    class Event(object):
        @classmethod
        def from_INOTIFY_HEADER(cls, in_header, path, filename=None):
            return cls(
                wd=in_header.wd,
                mask=in_header.mask,
                cookie=in_header.cookie,
                len_=in_header.len,
                dir_=bool(filename),
                path=path,
                filename=filename)

        def __init__(self, wd, mask, cookie, len_, dir_, path, filename=None):
            self.wd = wd
            self.mask = mask
            self.cookie = cookie
            self.len = len_
            self.path = path
            self.filename = filename
            self.dir = dir_

        def __str__(self):
            return ("{wd} {mask} {path} {filename} {dir}".format(
                wd=self.wd,
                mask=self.mask,
                path=self.path,
                filename=self.filename,
                dir=self.dir))

        def __repr__(self):
            return ("<Tail.Event(wd={wd}, mask={mask}, path={path}, "
                    "filename={filename}, dir={dir})>".format(
                        wd=self.wd,
                        mask=self.mask,
                        path=self.path,
                        filename=self.filename,
                        dir=self.dir))

    def __init__(self, filenames, block_duration_s=None, num_green_threads=10):
        # Eventlet monkeypatches the os module, so we disable these checks
        # pylint: disable=no-member
        if isinstance(filenames, six.string_types):
            filenames = [filenames]

        self.globs = [os.path.abspath(filename) for filename in filenames]
        # TODO: Handle expanding the greenpool if necessary
        kwargs = {}
        if block_duration_s:
            kwargs['block_duration_s'] = block_duration_s
        LOG.debug("creating inotify watch manager")
        self.watch_manager = inotify.adapters.Inotify(**kwargs)
        LOG.debug("")
        self.tails = {}
        self.dir_watches = {}
        self.thread = None
        self.pool = eventlet.greenpool.GreenPool(size=num_green_threads)

    # MAIN API

    def add_file(self, filepath):
        self.pool.spawn(self.process_tail, filepath)
        eventlet.sleep(0.01)

    def remove_file(self, filepath):
        self.pool.spawn(self._remove_file, filepath)
        eventlet.sleep(0.01)

    def run(self):
        self.update_tails(self.globs, do_read_all=False)
        try:
            for event in self.watch_manager.event_gen():
                if event:
                    (inotify_header, type_names, path, filename) = event
                    tail_event = Tail.Event.from_INOTIFY_HEADER(inotify_header, path, filename)
                    self.pool.spawn_n(self._inotify_event, tail_event)
                else:
                    eventlet.sleep()
                    if not self.should_run:
                        break
        finally:
            self.pool.waitall()
            self.remove_tails()

    # PRIVATE API

    def _remove_file(self, filepath):
        tail = self.tails.get(filepath)
        if tail:
            self.close_tail(tail)

    def _inotify_file(self, event):
        LOG.debug("file notified %r", event)
        tail = self.tails.get(event.path)
        if tail:
            if event.mask & in_constants.IN_MODIFY:
                if tail.rescan:
                    LOG.debug("rescanning %r", event.path)
                    self.process_tail(event.path)
                else:
                    LOG.debug("reading %r", tail)
                    self.read_tail(tail)
            else:
                tail.rescan = True

    def _inotify_dir(self, event):
        LOG.debug("dir notified %r", event)
        tail = self.tails.get(event.path)
        if tail:
            self.process_tail(event.path)

        if event.dir and not tail:
            self.update_tails(self.globs)

    def _inotify_event(self, event):
        LOG.debug("change notified %r", event)
        if event.dir:
            self._inotify_dir(event)
        else:
            self._inotify_file(event)
        eventlet.sleep()

    # INTERNAL TAIL API

    def read_tail(self, tail):
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

    def process_tail(self, path, should_seek=False):
        # pylint: disable=no-member
        file_stat = os.stat(path)

        LOG.debug("process_tail for %s", path)
        # Find or create a tail.
        tail = self.tails.get(path)
        if tail:
            fd_stat = os.fstat(tail.file_descriptor)
            pos = os.lseek(tail.file_descriptor, 0, os.SEEK_CUR)
            if fd_stat.st_size > pos:
                LOG.debug("something to read")
                self.read_tail(tail)
            if (tail.stat.st_size > file_stat.st_size or
                    tail.stat.st_ino != file_stat.st_ino):
                LOG.info("%s looks rotated. reopening", path)
                self.close_tail(tail)
                tail = None
                should_seek = False

        if not tail:
            LOG.info("tailing %s", path)
            self.tails[path] = tail = self.open_tail(path, should_seek)
            tail.stat = file_stat
            self.read_tail(tail)

        tail.rescan = False

    def update_tails(self, globs, do_read_all=True):
        # pylint: disable=no-member
        watches = set()

        LOG.debug("update tails: %r", globs)

        for fileglob in globs:
            for path in glob.iglob(fileglob):
                self.process_tail(path, not do_read_all)
                watches.add(path)

        for vanished in set(self.tails) - watches:
            LOG.info("%s vanished, stop tailing", vanished)
            self.close_tail(self.tails.pop(vanished))

        for path in globs:
            while len(path) > 1:
                path = os.path.dirname(path)
                if path not in self.dir_watches:
                    LOG.debug("monitoring dir %s", path)

                    self.dir_watches[path] = self.watch_manager.add_watch(
                        path, INOTIFY_DIR_MASK)

                if '*' not in path and '?' not in path:
                    break

    def remove_tails(self):
        LOG.debug("remove tails")

        for path, tail in self.tails.items():
            self.close_tail(tail)

    def open_tail(self, path, go_to_end=False):
        # pylint: disable=no-member
        tail = Tail.FileTail()
        tail.file_descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        tail.path = path

        if go_to_end:
            os.lseek(tail.file_descriptor, 0, os.SEEK_END)

        watch_descriptor = self.watch_manager.add_watch(
            path, INOTIFY_FILE_MASK)

        tail.watch_descriptor = watch_descriptor
        return tail

    def close_tail(self, tail):
        # pylint: disable=no-member
        self.watch_manager.remove_watch(tail.path)
        os.close(tail.file_descriptor)
        if tail.buffer:
            LOG.debug("triggering from tail buffer")
            self.handler(file_path=tail.path, line=tail.buffer)
