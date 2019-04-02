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

from __future__ import absolute_import

import tempfile

import six
import mock

from oslo_config import cfg
from oslo_config.cfg import ConfigFilesNotFoundError

from st2common import service_setup
from st2common.transport.bootstrap_utils import register_exchanges
from st2common.transport.bootstrap_utils import QUEUES
from st2common import config as st2common_config

from st2tests.base import CleanFilesTestCase
from st2tests import config

__all__ = [
    'ServiceSetupTestCase'
]

MOCK_LOGGING_CONFIG_INVALID_LOG_LEVEL = """
[loggers]
keys=root

[handlers]
keys=consoleHandler

[formatters]
keys=simpleConsoleFormatter

[logger_root]
level=invalid_log_level
handlers=consoleHandler

[handler_consoleHandler]
class=StreamHandler
level=DEBUG
formatter=simpleConsoleFormatter
args=(sys.stdout,)

[formatter_simpleConsoleFormatter]
class=st2common.logging.formatters.ConsoleLogFormatter
format=%(asctime)s %(levelname)s [-] %(message)s
datefmt=
""".strip()

MOCK_DEFAULT_CONFIG_FILE_PATH = '/etc/st2/st2.conf-test-patched'


def mock_get_logging_config_path():
    return ''


class ServiceSetupTestCase(CleanFilesTestCase):
    def test_no_logging_config_found(self):

        config.get_logging_config_path = mock_get_logging_config_path

        if six.PY3:
            expected_msg = ".*KeyError:.*"
        else:
            expected_msg = "No section: .*"

        self.assertRaisesRegexp(Exception, expected_msg,
                                service_setup.setup, service='api',
                                config=config,
                                setup_db=False, register_mq_exchanges=False,
                                register_signal_handlers=False,
                                register_internal_trigger_types=False,
                                run_migrations=False)

    def test_invalid_log_level_friendly_error_message(self):
        _, mock_logging_config_path = tempfile.mkstemp()
        self.to_delete_files.append(mock_logging_config_path)

        with open(mock_logging_config_path, 'w') as fp:
            fp.write(MOCK_LOGGING_CONFIG_INVALID_LOG_LEVEL)

        def mock_get_logging_config_path():
            return mock_logging_config_path

        config.get_logging_config_path = mock_get_logging_config_path

        if six.PY3:
            expected_msg = 'ValueError: Unknown level: \'invalid_log_level\''
            exc_type = ValueError
        else:
            expected_msg = 'Invalid log level selected. Log level names need to be all uppercase'
            exc_type = KeyError

        self.assertRaisesRegexp(exc_type, expected_msg,
                                service_setup.setup, service='api',
                                config=config,
                                setup_db=False, register_mq_exchanges=False,
                                register_signal_handlers=False,
                                register_internal_trigger_types=False,
                                run_migrations=False)

    @mock.patch('kombu.Queue.declare')
    def test_register_exchanges_predeclare_queues(self, mock_declare):
        # Verify that queues are correctly pre-declared
        self.assertEqual(mock_declare.call_count, 0)

        register_exchanges()
        self.assertEqual(mock_declare.call_count, len(QUEUES))

    @mock.patch('st2common.constants.system.DEFAULT_CONFIG_FILE_PATH',
            MOCK_DEFAULT_CONFIG_FILE_PATH)
    @mock.patch('st2common.config.DEFAULT_CONFIG_FILE_PATH', MOCK_DEFAULT_CONFIG_FILE_PATH)
    def test_service_setup_default_st2_conf_config_is_used(self):
        st2common_config.get_logging_config_path = mock_get_logging_config_path
        cfg.CONF.reset()

        # 1. DEFAULT_CONFIG_FILE_PATH config path should be used by default (/etc/st2/st2.conf)
        expected_msg = 'Failed to find some config files: %s' % (MOCK_DEFAULT_CONFIG_FILE_PATH)
        self.assertRaisesRegexp(ConfigFilesNotFoundError, expected_msg, service_setup.setup,
                                service='api',
                                config=st2common_config,
                                config_args=['--debug'],
                                setup_db=False, register_mq_exchanges=False,
                                register_signal_handlers=False,
                                register_internal_trigger_types=False,
                                run_migrations=False)

        cfg.CONF.reset()

        # 2. --config-file should still override default config file path option
        config_file_path = '/etc/st2/config.override.test'
        expected_msg = 'Failed to find some config files: %s' % (config_file_path)
        self.assertRaisesRegexp(ConfigFilesNotFoundError, expected_msg, service_setup.setup,
                                service='api',
                                config=st2common_config,
                                config_args=['--config-file', config_file_path],
                                setup_db=False, register_mq_exchanges=False,
                                register_signal_handlers=False,
                                register_internal_trigger_types=False,
                                run_migrations=False)
