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

import tempfile

from st2common import service_setup

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


class ServiceSetupTestCase(CleanFilesTestCase):
    def test_no_logging_config_found(self):
        def mock_get_logging_config_path():
            return ''

        config.get_logging_config_path = mock_get_logging_config_path

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

        expected_msg = 'Invalid log level selected. Log level names need to be all uppercase'
        self.assertRaisesRegexp(KeyError, expected_msg,
                                service_setup.setup, service='api',
                                config=config,
                                setup_db=False, register_mq_exchanges=False,
                                register_signal_handlers=False,
                                register_internal_trigger_types=False,
                                run_migrations=False)
