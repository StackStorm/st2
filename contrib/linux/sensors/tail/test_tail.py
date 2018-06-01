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
import shutil
import sys
import tempfile
import unittest

try:
    from StringIO import StringIO  # Python 2
except ImportError:
    from io import StringIO  # Python 3

import eventlet
import inotify

from .tail import Tail

LOG = logging.getLogger(__name__)


# https://stackoverflow.com/a/30716207
class ReplaceStdErr(object):
    """Context manager that replaces stderr with a StringIO object"""
    def __init__(self):
        self.original_stderr = sys.stderr

    def __enter__(self):
        sys.stderr = StringIO()

    def __exit__(self, type, value, traceback):
        sys.stderr = self.original_stderr


class TailTestCase(unittest.TestCase):

    def test_nonexisting_file(self):
        messages = []

        def message_handler(file_path, line):
            LOG.debug('event generated file_path: %s, line: %s', file_path, line)
            messages.append({'file_path': file_path, 'message': line})

        path = os.path.join('/', 'tmp', 'tail_test_case', 'this_file_should_never_exist')

        self.assertFalse(os.path.exists(path))

        tail = Tail(path)
        tail.set_handler(message_handler)
        thread = tail.start()

        with self.assertRaises(inotify.calls.InotifyError) as e:
            with ReplaceStdErr():
                LOG.debug("Waiting for thread to finish")
                thread.wait()  # give thread a chance to error out

            self.assertEqual(e.exception.message, "Call failed (should not be -1): (-1) ERRNO=(0)")

    def test_preexisting_file(self):
        messages = []

        def message_handler(file_path, line):
            LOG.debug('event generated file_path: %s, line: %s', file_path, line)
            messages.append({'file_path': file_path, 'message': line})

        with tempfile.NamedTemporaryFile() as f:
            f.write(b"test123\n")
            f.flush()

            tail = Tail(f.name)
            tail.set_handler(message_handler)
            tail.start()
            eventlet.sleep(0.01)  # give thread a chance to open the file

            f.write(b"second line\n")
            f.flush()
            eventlet.sleep(0.01)  # give thread a chance to read the line

            tail.stop()
            eventlet.sleep(0.01)  # give thread a chance to close the line

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["file_path"], f.name)
        self.assertEqual(messages[0]["message"], "second line")

    def test_write_without_newline(self):
        messages = []

        def message_handler(file_path, line):
            LOG.debug('event generated file_path: %s, line: %s', file_path, line)
            messages.append({'file_path': file_path, 'message': line})

        with tempfile.NamedTemporaryFile() as f:
            f.write(b"test123\n")
            f.flush()

            self.assertEqual(len(messages), 0)

            tail = Tail(f.name)
            tail.set_handler(message_handler)
            tail.start()
            eventlet.sleep(0.01)  # give thread a chance to open the file

            f.write(b"second line")
            f.flush()
            eventlet.sleep(0.01)  # give thread a chance to read the line

            self.assertEqual(len(messages), 0)

            f.write(b"\n")
            f.flush()
            eventlet.sleep(0.01)  # give thread a chance to read the line

            tail.stop()
            eventlet.sleep(0.01)  # give thread a chance to close the line

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["file_path"], f.name)
        self.assertEqual(messages[0]["message"], "second line")

    def test_write_with_newline_and_without_newline(self):
        messages = []

        def message_handler(file_path, line):
            LOG.debug('event generated file_path: %s, line: %s', file_path, line)
            messages.append({'file_path': file_path, 'message': line})

        with tempfile.NamedTemporaryFile() as f:
            f.write(b"test123\n")
            f.flush()

            self.assertEqual(len(messages), 0)

            tail = Tail(f.name)
            tail.set_handler(message_handler)
            tail.start()
            eventlet.sleep(0.01)  # give thread a chance to open the file

            f.write(b"second line\nthird ")
            f.flush()
            eventlet.sleep(0.01)  # give thread a chance to read the line

            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["file_path"], f.name)
            self.assertEqual(messages[0]["message"], "second line")

            f.write(b"line\n")
            f.flush()
            eventlet.sleep(0.01)  # give thread a chance to read the line

            tail.stop()
            eventlet.sleep(0.01)  # give thread a chance to close the line

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["file_path"], f.name)
        self.assertEqual(messages[0]["message"], "second line")
        self.assertEqual(messages[1]["file_path"], f.name)
        self.assertEqual(messages[1]["message"], "third line")

    def test_write_after_newline(self):
        messages = []

        def message_handler(file_path, line):
            LOG.debug('event generated file_path: %s, line: %s', file_path, line)
            messages.append({'file_path': file_path, 'message': line})

        with tempfile.NamedTemporaryFile() as f:
            f.write(b"test123\n")
            f.flush()

            self.assertEqual(len(messages), 0)

            tail = Tail(f.name)
            tail.set_handler(message_handler)
            tail.start()
            eventlet.sleep(0.01)  # give thread a chance to open the file

            f.write(b"second line\nthird")
            f.flush()
            eventlet.sleep(0.01)  # give thread a chance to read the line

            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["file_path"], f.name)
            self.assertEqual(messages[0]["message"], "second line")

            tail.stop()
            eventlet.sleep(0.01)  # give thread a chance to close the line

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["file_path"], f.name)
        self.assertEqual(messages[0]["message"], "second line")
        self.assertEqual(messages[1]["file_path"], f.name)
        self.assertEqual(messages[1]["message"], "third")

    def test_wildcard(self):
        messages = []

        def message_handler(file_path, line):
            LOG.debug('event generated file_path: %s, line: %s', file_path, line)
            messages.append({'file_path': file_path, 'message': line})

        try:
            path = tempfile.mkdtemp()
            tail = Tail(os.path.join(path, "*.log"))
            tail.set_handler(message_handler)
            tail.start()
            eventlet.sleep(0.01)  # give thread a chance to open the file

            LOG.debug("about to write line 1")
            with open(os.path.join(path, "test.log"), 'w') as f:
                f.write("line 1\n")

            eventlet.sleep(0.01)  # give thread a chance to read the line
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["message"], "line 1")

            LOG.debug("about to write line 2")
            with open(os.path.join(path, "test.log"), 'a') as f:
                f.write("line 2\n")

            eventlet.sleep(0.01)  # give thread a chance to read the line
            self.assertEqual(len(messages), 2)
            self.assertEqual(messages[0]["file_path"], os.path.join(path, "test.log"))
            self.assertEqual(messages[0]["message"], "line 1")
            self.assertEqual(messages[1]["file_path"], os.path.join(path, "test.log"))
            self.assertEqual(messages[1]["message"], "line 2")

            tail.stop()
            eventlet.sleep(0.1)  # give thread a chance to close the line

        finally:
            shutil.rmtree(path)
