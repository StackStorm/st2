# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import os
import uuid
import tempfile
import logging as logbase

from st2common import log as logging
from st2common.logging.formatters import ConsoleLogFormatter
import st2tests.config as tests_config

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
RESOURCES_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '../resources'))
CONFIG_FILE_PATH = os.path.join(RESOURCES_DIR, 'logging.conf')


class MockRecord(object):
    levelno = 40
    exc_info = None
    exc_text = None


class LoggerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    def setUp(self):
        super(LoggerTestCase, self).setUp()
        self.config_text = open(CONFIG_FILE_PATH).read()
        self.cfg_fd, self.cfg_path = tempfile.mkstemp()
        self.info_log_fd, self.info_log_path = tempfile.mkstemp()
        self.audit_log_fd, self.audit_log_path = tempfile.mkstemp()
        with open(self.cfg_path, 'a') as f:
            f.write(self.config_text.format(self.info_log_path,
                                            self.audit_log_path))

    def tearDown(self):
        self._remove_tempfile(self.cfg_fd, self.cfg_path)
        self._remove_tempfile(self.info_log_fd, self.info_log_path)
        self._remove_tempfile(self.audit_log_fd, self.audit_log_path)
        super(LoggerTestCase, self).tearDown()

    def _remove_tempfile(self, fd, path):
        os.close(fd)
        os.unlink(path)

    def test_logger_setup_failure(self):
        config_file = '/tmp/abc123'
        self.assertFalse(os.path.exists(config_file))
        self.assertRaises(Exception, logging.setup, config_file)

    def test_logger_set_level(self):
        logging.setup(self.cfg_path)
        log = logging.getLogger(__name__)
        self.assertEqual(log.getEffectiveLevel(), logbase.DEBUG)
        log.setLevel(logbase.INFO)
        self.assertEqual(log.getEffectiveLevel(), logbase.INFO)
        log.setLevel(logbase.WARN)
        self.assertEqual(log.getEffectiveLevel(), logbase.WARN)
        log.setLevel(logbase.ERROR)
        self.assertEqual(log.getEffectiveLevel(), logbase.ERROR)
        log.setLevel(logbase.CRITICAL)
        self.assertEqual(log.getEffectiveLevel(), logbase.CRITICAL)
        log.setLevel(logbase.AUDIT)
        self.assertEqual(log.getEffectiveLevel(), logbase.AUDIT)

    def test_log_info(self):
        """Test that INFO log entry does not go to the audit log."""
        logging.setup(self.cfg_path)
        log = logging.getLogger(__name__)
        msg = uuid.uuid4().hex
        log.info(msg)
        info_log_entries = open(self.info_log_path).read()
        self.assertIn(msg, info_log_entries)
        audit_log_entries = open(self.audit_log_path).read()
        self.assertNotIn(msg, audit_log_entries)

    def test_log_critical(self):
        """Test that CRITICAL log entry does not go to the audit log."""
        logging.setup(self.cfg_path)
        log = logging.getLogger(__name__)
        msg = uuid.uuid4().hex
        log.critical(msg)
        info_log_entries = open(self.info_log_path).read()
        self.assertIn(msg, info_log_entries)
        audit_log_entries = open(self.audit_log_path).read()
        self.assertNotIn(msg, audit_log_entries)

    def test_log_audit(self):
        """Test that AUDIT log entry goes to the audit log."""
        logging.setup(self.cfg_path)
        log = logging.getLogger(__name__)
        msg = uuid.uuid4().hex
        log.audit(msg)
        info_log_entries = open(self.info_log_path).read()
        self.assertIn(msg, info_log_entries)
        audit_log_entries = open(self.audit_log_path).read()
        self.assertIn(msg, audit_log_entries)


class ConsoleLogFormatterTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    def test_format(self):
        formatter = ConsoleLogFormatter()

        # No extra attributes
        mock_message = 'test message 1'

        record = MockRecord()
        record.getMessage = lambda: mock_message

        message = formatter.format(record=record)
        self.assertEqual(message, mock_message)

        # Some extra attributes
        mock_message = 'test message 2'
        record = MockRecord()

        # Add "extra" attributes
        record._user_id = 1
        record._value = 'bar'
        record.ignored = 'foo'  # this one is ignored since it doesnt have a prefix
        record.getMessage = lambda: mock_message

        message = formatter.format(record=record)
        expected = 'test message 2 (value=\'bar\',user_id=1)'
        self.assertEqual(message, expected)
