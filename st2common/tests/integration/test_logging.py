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

# Ignore CryptographyDeprecationWarning warnings which appear on Python 3.6
# TODO: Remove after dropping python3.6
import warnings

warnings.filterwarnings("ignore", message="Python 3.6 is no longer supported")

import os
import sys
import signal
import pytest

import eventlet
from eventlet.green import subprocess

from st2tests.base import IntegrationTestCase

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEST_FILE_PATH = os.path.join(BASE_DIR, "log_unicode_data.py")


class LogFormattingAndEncodingTestCase(IntegrationTestCase):
    def test_formatting_with_unicode_data_works_no_stdout_patching_valid_utf8_encoding(
        self,
    ):
        # Ensure that process doesn't end up in an infinite loop if non-utf8 locale / encoding is
        # used and a unicode sequence is logged.

        # 1. Process is using a utf-8 encoding
        process = self._start_process(
            env={
                "LC_ALL": "en_US.UTF-8",
                "ST2_LOG_PATCH_STDOUT": "false",
                "PYTHONIOENCODING": "utf-8",
            }
        )
        self.add_process(process=process)

        # Give it some time to start up and run for a while
        eventlet.sleep(2)
        process.send_signal(signal.SIGKILL)

        stdout = process.stdout.read().decode("utf-8").strip()
        stderr = process.stderr.read().decode("utf-8").strip()
        stdout_lines = stdout.split("\n")

        self.assertEqual(stderr, "")
        self.assertTrue(len(stdout_lines) < 20)

        self.assertIn("INFO [-] Test info message 1", stdout)
        self.assertIn("Test debug message 1", stdout)
        self.assertIn("INFO [-] Test info message with unicode 1 - 好好好", stdout)
        self.assertIn("DEBUG [-] Test debug message with unicode 1 - 好好好", stdout)
        self.assertIn(
            "INFO [-] Test info message with unicode 1 - \u597d\u597d\u597d", stdout
        )
        self.assertIn(
            "DEBUG [-] Test debug message with unicode 1 - \u597d\u597d\u597d", stdout
        )

    @pytest.mark.skipif(
        sys.version_info >= (3, 8, 0), reason="Skipping test under Python >= 3.8"
    )
    def test_formatting_with_unicode_data_works_no_stdout_patching_non_valid_utf8_encoding(
        self,
    ):
        # Ensure that process doesn't end up in an infinite loop if non-utf8 locale / encoding is
        # used and a unicode sequence is logged.

        # 2. Process is not using utf-8 encoding - LC_ALL set to invalid locale - should result in
        # single exception being logged, but not infinite loop
        process = self._start_process(
            env={
                "LC_ALL": "invalid",
                "ST2_LOG_PATCH_STDOUT": "false",
                "PYTHONIOENCODING": "utf-8",
            }
        )
        self.add_process(process=process)

        # Give it some time to start up and run for a while
        eventlet.sleep(2)
        process.send_signal(signal.SIGKILL)

        stdout = process.stdout.read().decode("utf-8")
        stderr = process.stderr.read().decode("utf-8")
        stdout_lines = stdout.split("\n")

        self.assertEqual(stderr, "")

        self.assertIn("ERROR [-]   ", stdout)
        self.assertIn("can't encode", stdout)
        self.assertIn("'ascii' codec can't encode", stdout)

        self.assertTrue(len(stdout_lines) >= 50)
        self.assertTrue(len(stdout_lines) < 100)

        self.assertIn("INFO [-] Test info message 1", stdout)
        self.assertIn("Test debug message 1", stdout)
        self.assertIn("INFO [-] Test info message with unicode 1 - 好好好", stdout)
        self.assertIn("DEBUG [-] Test debug message with unicode 1 - 好好好", stdout)
        self.assertIn(
            "INFO [-] Test info message with unicode 1 - \u597d\u597d\u597d", stdout
        )
        self.assertIn(
            "DEBUG [-] Test debug message with unicode 1 - \u597d\u597d\u597d", stdout
        )

    def test_formatting_with_unicode_data_works_no_stdout_patching_ascii_pythonioencoding(
        self,
    ):
        # Ensure that process doesn't end up in an infinite loop if non-utf8 locale / encoding is
        # used and a unicode sequence is logged.

        # 3. Process is not using utf-8 encoding - PYTHONIOENCODING set to ascii - should result in
        # single exception being logged, but not infinite loop
        process = self._start_process(
            env={
                "LC_ALL": "en_US.UTF-8",
                "ST2_LOG_PATCH_STDOUT": "false",
                "PYTHONIOENCODING": "ascii",
            }
        )
        self.add_process(process=process)

        # Give it some time to start up and run for a while
        eventlet.sleep(2)
        process.send_signal(signal.SIGKILL)

        stdout = process.stdout.read().decode("utf-8")
        stderr = process.stderr.read().decode("utf-8")
        stdout_lines = stdout.split("\n")

        self.assertEqual(stderr, "")

        self.assertIn("ERROR [-]   ", stdout)
        self.assertIn("can't encode", stdout)
        self.assertIn("'ascii' codec can't encode", stdout)

        self.assertTrue(len(stdout_lines) >= 50)
        self.assertTrue(len(stdout_lines) < 100)

        self.assertIn("INFO [-] Test info message 1", stdout)
        self.assertIn("Test debug message 1", stdout)
        self.assertNotIn("INFO [-] Test info message with unicode 1 - 好好好", stdout)
        self.assertNotIn("DEBUG [-] Test debug message with unicode 1 - 好好好", stdout)
        self.assertNotIn(
            "INFO [-] Test info message with unicode 1 - \u597d\u597d\u597d", stdout
        )
        self.assertNotIn(
            "DEBUG [-] Test debug message with unicode 1 - \u597d\u597d\u597d", stdout
        )

    def test_formatting_with_unicode_data_works_with_stdout_patching_valid_utf8_encoding(
        self,
    ):
        # Test a scenario where patching is enabled which means it should never result in infinite
        # loop
        # 1. Process is using a utf-8 encoding
        process = self._start_process(
            env={
                "LC_ALL": "en_US.UTF-8",
                "ST2_LOG_PATCH_STDOUT": "true",
                "PYTHONIOENCODING": "utf-8",
            }
        )
        self.add_process(process=process)

        # Give it some time to start up and run for a while
        eventlet.sleep(2)
        process.send_signal(signal.SIGKILL)

        stdout = process.stdout.read().decode("utf-8")
        stderr = process.stderr.read().decode("utf-8")
        stdout_lines = stdout.split("\n")

        self.assertEqual(stderr, "")
        self.assertTrue(len(stdout_lines) < 20)

        self.assertIn("INFO [-] Test info message 1", stdout)
        self.assertIn("Test debug message 1", stdout)
        self.assertIn("INFO [-] Test info message with unicode 1 - 好好好", stdout)
        self.assertIn("DEBUG [-] Test debug message with unicode 1 - 好好好", stdout)
        self.assertIn(
            "INFO [-] Test info message with unicode 1 - \u597d\u597d\u597d", stdout
        )
        self.assertIn(
            "DEBUG [-] Test debug message with unicode 1 - \u597d\u597d\u597d", stdout
        )

    def test_formatting_with_unicode_data_works_with_stdout_patching_non_valid_utf8_encoding(
        self,
    ):
        # 2. Process is not using utf-8 encoding
        process = self._start_process(
            env={
                "LC_ALL": "invalid",
                "ST2_LOG_PATCH_STDOUT": "true",
                "PYTHONIOENCODING": "utf-8",
            }
        )
        self.add_process(process=process)

        # Give it some time to start up and run for a while
        eventlet.sleep(2)
        process.send_signal(signal.SIGKILL)

        stdout = process.stdout.read().decode("utf-8")
        stderr = process.stderr.read().decode("utf-8")
        stdout_lines = stdout.split("\n")

        self.assertEqual(stderr, "")
        print(stdout)
        self.assertTrue(len(stdout_lines) < 100)

        self.assertIn("INFO [-] Test info message 1", stdout)
        self.assertIn("Test debug message 1", stdout)
        self.assertIn("INFO [-] Test info message with unicode 1 - 好好好", stdout)
        self.assertIn("DEBUG [-] Test debug message with unicode 1 - 好好好", stdout)
        self.assertIn(
            "INFO [-] Test info message with unicode 1 - \u597d\u597d\u597d", stdout
        )
        self.assertIn(
            "DEBUG [-] Test debug message with unicode 1 - \u597d\u597d\u597d", stdout
        )

    def test_formatting_with_unicode_data_works_with_stdout_patching__ascii_pythonioencoding(
        self,
    ):
        # 3. Process is not using utf-8 encoding - PYTHONIOENCODING set to ascii
        process = self._start_process(
            env={
                "LC_ALL": "en_US.UTF-8",
                "ST2_LOG_PATCH_STDOUT": "true",
                "PYTHONIOENCODING": "ascii",
            }
        )
        self.add_process(process=process)

        # Give it some time to start up and run for a while
        eventlet.sleep(2)
        process.send_signal(signal.SIGKILL)

        stdout = process.stdout.read().decode("utf-8")
        stderr = process.stderr.read().decode("utf-8")
        stdout_lines = stdout.split("\n")

        self.assertEqual(stderr, "")

        self.assertTrue(len(stdout_lines) < 20)

        self.assertIn("Patching sys.stdout", stdout)
        self.assertIn("INFO [-] Test info message 1", stdout)
        self.assertIn("Test debug message 1", stdout)
        self.assertIn("INFO [-] Test info message with unicode 1 - 好好好", stdout)
        self.assertIn("DEBUG [-] Test debug message with unicode 1 - 好好好", stdout)
        self.assertIn(
            "INFO [-] Test info message with unicode 1 - \u597d\u597d\u597d", stdout
        )
        self.assertIn(
            "DEBUG [-] Test debug message with unicode 1 - \u597d\u597d\u597d", stdout
        )

    def _start_process(self, env=None):
        cmd = [sys.executable, TEST_FILE_PATH]
        process = subprocess.Popen(
            cmd,
            env=env or os.environ.copy(),
            cwd=os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            preexec_fn=os.setsid,
        )
        return process
