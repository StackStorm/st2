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

from __future__ import absolute_import

import tempfile

import mock

from oslo_config.cfg import ConfigFilesNotFoundError

from st2common import service_setup
from st2common.services import coordination
from st2common.transport.bootstrap_utils import register_exchanges
from st2common.transport.bootstrap_utils import QUEUES

from st2tests.base import CleanFilesTestCase
from st2tests import config

__all__ = ["ServiceSetupTestCase"]

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

MOCK_LOGGING_CONFIG_VALID = """
[loggers]
keys=root

[handlers]
keys=consoleHandler

[formatters]
keys=simpleConsoleFormatter

[logger_root]
level=DEBUG
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


MOCK_DEFAULT_CONFIG_FILE_PATH = "/etc/st2/st2.conf-test-patched"


def mock_get_logging_config_path():
    return ""


class ServiceSetupTestCase(CleanFilesTestCase):
    def setUp(self):
        super(ServiceSetupTestCase, self).setUp()
        config.USE_DEFAULT_CONFIG_FILES = False

    def tearDown(self):
        super(ServiceSetupTestCase, self).tearDown()
        config.USE_DEFAULT_CONFIG_FILES = False

    def test_no_logging_config_found(self):
        config.get_logging_config_path = mock_get_logging_config_path

        expected_msg = ".*KeyError:.*"

        self.assertRaisesRegex(
            Exception,
            expected_msg,
            service_setup.setup,
            service="api",
            config=config,
            setup_db=False,
            register_mq_exchanges=False,
            register_signal_handlers=False,
            register_internal_trigger_types=False,
            run_migrations=False,
        )

    def test_invalid_log_level_friendly_error_message(self):
        _, mock_logging_config_path = tempfile.mkstemp()
        self.to_delete_files.append(mock_logging_config_path)

        with open(mock_logging_config_path, "w") as fp:
            fp.write(MOCK_LOGGING_CONFIG_INVALID_LOG_LEVEL)

        def mock_get_logging_config_path():
            return mock_logging_config_path

        config.get_logging_config_path = mock_get_logging_config_path

        expected_msg = "ValueError: Unknown level: 'invalid_log_level'"
        exc_type = ValueError

        self.assertRaisesRegex(
            exc_type,
            expected_msg,
            service_setup.setup,
            service="api",
            config=config,
            setup_db=False,
            register_mq_exchanges=False,
            register_signal_handlers=False,
            register_internal_trigger_types=False,
            run_migrations=False,
        )

    @mock.patch("kombu.Queue.declare")
    def test_register_exchanges_predeclare_queues(self, mock_declare):
        # Verify that queues are correctly pre-declared
        self.assertEqual(mock_declare.call_count, 0)

        register_exchanges()
        self.assertEqual(mock_declare.call_count, len(QUEUES))

    @mock.patch(
        "st2tests.config.DEFAULT_CONFIG_FILE_PATH", MOCK_DEFAULT_CONFIG_FILE_PATH
    )
    def test_service_setup_default_st2_conf_config_is_used(self):
        config.USE_DEFAULT_CONFIG_FILES = True

        _, mock_logging_config_path = tempfile.mkstemp()
        self.to_delete_files.append(mock_logging_config_path)

        with open(mock_logging_config_path, "w") as fp:
            fp.write(MOCK_LOGGING_CONFIG_VALID)

        def mock_get_logging_config_path():
            return mock_logging_config_path

        config.get_logging_config_path = mock_get_logging_config_path

        # 1. DEFAULT_CONFIG_FILE_PATH config path should be used by default (/etc/st2/st2.conf)
        expected_msg = "Failed to find some config files: %s" % (
            MOCK_DEFAULT_CONFIG_FILE_PATH
        )
        self.assertRaisesRegex(
            ConfigFilesNotFoundError,
            expected_msg,
            service_setup.setup,
            service="api",
            config=config,
            config_args=["--debug"],
            setup_db=False,
            register_mq_exchanges=False,
            register_signal_handlers=False,
            register_internal_trigger_types=False,
            run_migrations=False,
            register_runners=False,
        )

        # 2. --config-file should still override default config file path option
        config_file_path = "/etc/st2/config.override.test"
        expected_msg = "Failed to find some config files: %s" % (config_file_path)
        self.assertRaisesRegex(
            ConfigFilesNotFoundError,
            expected_msg,
            service_setup.setup,
            service="api",
            config=config,
            config_args=["--config-file", config_file_path],
            setup_db=False,
            register_mq_exchanges=False,
            register_signal_handlers=False,
            register_internal_trigger_types=False,
            run_migrations=False,
            register_runners=False,
        )

    def test_deregister_service_when_service_registry_enabled(self):
        service = "api"
        service_setup.register_service_in_service_registry(
            service, capabilities={"hostname": "", "pid": ""}
        )
        coordinator = coordination.get_coordinator(start_heart=True)
        members = coordinator.get_members(service.encode("utf-8"))
        self.assertEqual(len(list(members.get())), 1)
        service_setup.deregister_service(service)
        members = coordinator.get_members(service.encode("utf-8"))
        self.assertEqual(len(list(members.get())), 0)

    def test_deregister_service_when_service_registry_disables(self):
        service = "api"
        try:
            service_setup.deregister_service(service)
        except:
            assert False, "service_setup.deregister_service raised exception"

        assert True
