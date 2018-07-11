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
import tempfile
import time
import unittest2

from tail import Tail

LOG = logging.getLogger(__name__)


class TailTestCase(unittest2.TestCase):

    def test_nonexisting_file(self):
        path = os.path.join('/', 'tmp', 'tail_test_case', 'this_file_should_never_exist')

        self.assertFalse(os.path.exists(path))

        with self.assertRaises(OSError):
            Tail(filenames=path)

    def test_preexisting_file(self):
        messages = []

        def message_handler(file_path, line):
            LOG.debug('event generated file_path: %s, line: %s', file_path, line)
            messages.append({'file_path': file_path, 'message': line})

        with tempfile.NamedTemporaryFile() as f:
            f.write(b"test123\n")
            f.flush()

            tail = Tail(handler=message_handler, filenames=[])

            tail.add_file(f.name)

            tail.start()

            f.write(b"second line\n")
            f.flush()

            time.sleep(1)

            tail.stop()

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

            tail = Tail(filenames=f.name)
            tail.set_handler(message_handler)
            tail.start()

            f.write(b"second line")
            f.flush()

            self.assertEqual(len(messages), 0)

            f.write(b"\n")
            f.flush()

            time.sleep(1)

            tail.stop()

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

            tail = Tail(filenames=f.name)
            tail.set_handler(message_handler)
            tail.start()

            f.write(b"second line\nthird ")
            f.flush()

            time.sleep(1)

            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["file_path"], f.name)
            self.assertEqual(messages[0]["message"], "second line")

            f.write(b"line\n")
            f.flush()

            time.sleep(1)

            tail.stop()

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

            tail = Tail(filenames=f.name)
            tail.set_handler(message_handler)
            tail.start()

            f.write(b"second line\nthird")
            f.flush()

            time.sleep(1)

            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]["file_path"], f.name)
            self.assertEqual(messages[0]["message"], "second line")

            tail.stop()

        time.sleep(1)

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["file_path"], f.name)
        self.assertEqual(messages[0]["message"], "second line")
        self.assertEqual(messages[1]["file_path"], f.name)
        self.assertEqual(messages[1]["message"], "third")


if __name__ == '__main__':
    unittest2.main()
