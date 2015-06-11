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
import sys
import json
import uuid
import tempfile
import logging as logbase

import mock

from st2common import log as logging
from st2common.logging.formatters import ConsoleLogFormatter
from st2common.logging.formatters import GelfLogFormatter
from st2common.logging.formatters import MASKED_ATTRIBUTE_VALUE
from st2common.models.db.action import ActionDB
from st2common.models.db.execution import ActionExecutionDB
import st2tests.config as tests_config

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
RESOURCES_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '../resources'))
CONFIG_FILE_PATH = os.path.join(RESOURCES_DIR, 'logging.conf')

MOCK_MASKED_ATTRIBUTES = [
    'blacklisted_1',
    'blacklisted_2',
    'blacklisted_3',
]


class MockRecord(object):
    levelno = 40
    msg = None
    exc_info = None
    exc_text = None

    def getMessage(self):
        return self.msg


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
        record.msg = mock_message

        message = formatter.format(record=record)
        self.assertEqual(message, mock_message)

        # Some extra attributes
        mock_message = 'test message 2'

        record = MockRecord()
        record.msg = mock_message

        # Add "extra" attributes
        record._user_id = 1
        record._value = 'bar'
        record.ignored = 'foo'  # this one is ignored since it doesnt have a prefix

        message = formatter.format(record=record)
        expected = 'test message 2 (value=\'bar\',user_id=1)'
        self.assertEqual(message, expected)

    @mock.patch('st2common.logging.formatters.MASKED_ATTRIBUTES', MOCK_MASKED_ATTRIBUTES)
    def test_format_blacklisted_attributes_are_masked(self):
        formatter = ConsoleLogFormatter()

        mock_message = 'test message 1'

        record = MockRecord()
        record.msg = mock_message

        # Add "extra" attributes
        record._blacklisted_1 = 'test value 1'
        record._blacklisted_2 = 'test value 2'
        record._blacklisted_3 = {'key1': 'val1', 'blacklisted_1': 'val2', 'key3': 'val3'}
        record._foo1 = 'bar'

        message = formatter.format(record=record)
        expected = ("test message 1 (blacklisted_1='********',blacklisted_2='********',"
                    "blacklisted_3={'key3': 'val3', 'key1': 'val1', 'blacklisted_1': '********'},"
                    "foo1='bar')")
        self.assertEqual(message, expected)

    @mock.patch('st2common.logging.formatters.MASKED_ATTRIBUTES', MOCK_MASKED_ATTRIBUTES)
    def test_format_secret_action_parameters_are_masked(self):
        formatter = ConsoleLogFormatter()

        mock_message = 'test message 1'

        mock_action_db = ActionDB()
        mock_action_db.name = 'test.action'
        mock_action_db.pack = 'testpack'
        mock_action_db.parameters = {
            'parameter1': {
                'type': 'string',
                'required': False
            },
            'parameter2': {
                'type': 'string',
                'required': False,
                'secret': True
            }
        }

        mock_action_execution_db = ActionExecutionDB()
        mock_action_execution_db.action = mock_action_db.to_serializable_dict()
        mock_action_execution_db.parameters = {
            'parameter1': 'value1',
            'parameter2': 'value2'
        }

        record = MockRecord()
        record.msg = mock_message

        # Add "extra" attributes
        record._action_execution_db = mock_action_execution_db

        expected_msg_part = "'parameters': {'parameter1': 'value1', 'parameter2': '********'}"

        message = formatter.format(record=record)
        self.assertTrue('test message 1' in message)
        self.assertTrue(expected_msg_part in message)


class GelfLogFormatterTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    def test_format(self):
        formatter = GelfLogFormatter()

        expected_keys = ['version', 'host', 'short_message', 'full_message',
                         'timestamp', 'level']

        # No extra attributes
        mock_message = 'test message 1'

        record = MockRecord()
        record.msg = mock_message

        message = formatter.format(record=record)
        parsed = json.loads(message)

        for key in expected_keys:
            self.assertTrue(key in parsed)

        self.assertEqual(parsed['short_message'], mock_message)
        self.assertEqual(parsed['full_message'], mock_message)

        # Some extra attributes
        mock_message = 'test message 2'

        record = MockRecord()
        record.msg = mock_message

        # Add "extra" attributes
        record._user_id = 1
        record._value = 'bar'
        record.ignored = 'foo'  # this one is ignored since it doesnt have a prefix

        message = formatter.format(record=record)
        parsed = json.loads(message)

        for key in expected_keys:
            self.assertTrue(key in parsed)

        self.assertEqual(parsed['short_message'], mock_message)
        self.assertEqual(parsed['full_message'], mock_message)
        self.assertEqual(parsed['_user_id'], 1)
        self.assertEqual(parsed['_value'], 'bar')
        self.assertTrue('ignored' not in parsed)

        # Record with an exception
        mock_exception = Exception('mock exception bar')

        try:
            raise mock_exception
        except Exception:
            mock_exc_info = sys.exc_info()

        # Some extra attributes
        mock_message = 'test message 3'

        record = MockRecord()
        record.msg = mock_message
        record.exc_info = mock_exc_info

        message = formatter.format(record=record)
        parsed = json.loads(message)

        for key in expected_keys:
            self.assertTrue(key in parsed)

        self.assertEqual(parsed['short_message'], mock_message)
        self.assertTrue(mock_message in parsed['full_message'])
        self.assertTrue('Traceback' in parsed['full_message'])
        self.assertTrue('_exception' in parsed)
        self.assertTrue('_traceback' in parsed)

    def test_extra_object_serialization(self):
        class MyClass1(object):
            def __repr__(self):
                return 'repr'

        class MyClass2(object):
            def to_dict(self):
                return 'to_dict'

        class MyClass3(object):
            def to_serializable_dict(self, mask_secrets=False):
                return 'to_serializable_dict'

        formatter = GelfLogFormatter()

        record = MockRecord()
        record.msg = 'message'
        record._obj1 = MyClass1()
        record._obj2 = MyClass2()
        record._obj3 = MyClass3()

        message = formatter.format(record=record)
        parsed = json.loads(message)
        self.assertEqual(parsed['_obj1'], 'repr')
        self.assertEqual(parsed['_obj2'], 'to_dict')
        self.assertEqual(parsed['_obj3'], 'to_serializable_dict')

    @mock.patch('st2common.logging.formatters.MASKED_ATTRIBUTES', MOCK_MASKED_ATTRIBUTES)
    def test_format_blacklisted_attributes_are_masked(self):
        formatter = GelfLogFormatter()

        # Some extra attributes
        mock_message = 'test message 1'

        record = MockRecord()
        record.msg = mock_message

        # Add "extra" attributes
        record._blacklisted_1 = 'test value 1'
        record._blacklisted_2 = 'test value 2'
        record._blacklisted_3 = {'key1': 'val1', 'blacklisted_1': 'val2', 'key3': 'val3'}
        record._foo1 = 'bar'

        message = formatter.format(record=record)
        parsed = json.loads(message)

        self.assertEqual(parsed['_blacklisted_1'], MASKED_ATTRIBUTE_VALUE)
        self.assertEqual(parsed['_blacklisted_2'], MASKED_ATTRIBUTE_VALUE)
        self.assertEqual(parsed['_blacklisted_3']['key1'], 'val1')
        self.assertEqual(parsed['_blacklisted_3']['blacklisted_1'], MASKED_ATTRIBUTE_VALUE)
        self.assertEqual(parsed['_blacklisted_3']['key3'], 'val3')
        self.assertEqual(parsed['_foo1'], 'bar')

        # Assert that the original dict is left unmodified
        self.assertEqual(record._blacklisted_1, 'test value 1')
        self.assertEqual(record._blacklisted_2, 'test value 2')
        self.assertEqual(record._blacklisted_3['key1'], 'val1')
        self.assertEqual(record._blacklisted_3['blacklisted_1'], 'val2')
        self.assertEqual(record._blacklisted_3['key3'], 'val3')
