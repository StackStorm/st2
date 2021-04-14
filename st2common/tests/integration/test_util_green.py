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

import os

from io import BytesIO

import greenlet

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

from st2tests.base import IntegrationTestCase

from st2common.util.green.shell import run_command
from st2common.util.green.shell import TIMEOUT_EXIT_CODE
from st2common.util.shell import kill_process
from st2common.util.shell import quote_unix

_all__ = ["GreenShellUtilsTestCase"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class GreenShellUtilsTestCase(IntegrationTestCase):
    def test_run_command_success(self):
        # 0 exit code
        exit_code, stdout, stderr, timed_out = run_command(
            cmd='echo "test stdout" ; >&2 echo "test stderr"', shell=True
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.strip(), b"test stdout")
        self.assertEqual(stderr.strip(), b"test stderr")
        self.assertFalse(timed_out)

        # non-zero exit code
        exit_code, stdout, stderr, timed_out = run_command(
            cmd='echo "test stdout" ; >&2 echo "test stderr" ; exit 5', shell=True
        )
        self.assertEqual(exit_code, 5)
        self.assertEqual(stdout.strip(), b"test stdout")
        self.assertEqual(stderr.strip(), b"test stderr")
        self.assertFalse(timed_out)

        # implicit non zero code (invalid command)
        exit_code, stdout, stderr, timed_out = run_command(
            cmd="foobarbarbazrbar", shell=True
        )
        self.assertEqual(exit_code, 127)
        self.assertEqual(stdout.strip(), b"")
        self.assertTrue(b"foobarbarbazrbar: not found" in stderr.strip())
        self.assertFalse(timed_out)

    def test_run_command_timeout_shell_and_custom_kill_func(self):
        # This test represents our local runner setup where we use a preexec_func + custom kill_func
        # NOTE: When using shell=True. we should alaways use custom kill_func to ensure child shell
        # processses are in fact killed as well.
        exit_code, stdout, stderr, timed_out = run_command(
            cmd='echo "pre sleep";  sleep 1589; echo "post sleep"',
            preexec_func=os.setsid,
            timeout=1,
            kill_func=kill_process,
            shell=True,
        )
        self.assertEqual(exit_code, TIMEOUT_EXIT_CODE)
        self.assertEqual(stdout.strip(), b"pre sleep")
        self.assertEqual(stderr.strip(), b"")
        self.assertTrue(timed_out)

        # Verify there is no zombie process left laying around
        self.assertNoStrayProcessesLeft("sleep 1589")

    def test_run_command_timeout_shell_and_custom_kill_func_and_read_funcs(self):
        # This test represents our local runner setup where we use a preexec_func + custom kill_func
        # NOTE: When using shell=True. we should alaways use custom kill_func to ensure child shell
        # processses are in fact killed as well.
        def mock_read_stdout(process_stdout, stdout_buffer):
            stdout_buffer.write(process_stdout.read())

        def mock_read_stderr(process_stderr, stderr_buffer):
            stderr_buffer.write(process_stderr.read())

        read_stdout_buffer = BytesIO()
        read_stderr_buffer = BytesIO()

        exit_code, stdout, stderr, timed_out = run_command(
            cmd='echo "pre sleep"; >&2 echo "pre sleep stderr" ; sleep 1589; echo "post sleep"',
            preexec_func=os.setsid,
            timeout=1,
            kill_func=kill_process,
            shell=True,
            read_stdout_func=mock_read_stdout,
            read_stderr_func=mock_read_stderr,
            read_stdout_buffer=read_stdout_buffer,
            read_stderr_buffer=read_stderr_buffer,
        )
        self.assertEqual(exit_code, TIMEOUT_EXIT_CODE)
        self.assertEqual(stdout.strip(), b"pre sleep")
        self.assertEqual(stderr.strip(), b"pre sleep stderr")
        self.assertTrue(timed_out)

        # Only initial produced line should be read
        self.assertEqual(read_stdout_buffer.getvalue().strip(), b"pre sleep")
        self.assertEqual(read_stderr_buffer.getvalue().strip(), b"pre sleep stderr")

        # Verify there is no zombie process left laying around
        self.assertNoStrayProcessesLeft("sleep 1589")

    def test_run_command_timeout_no_shell_no_custom_kill_func(self):
        exit_code, stdout, stderr, timed_out = run_command(
            cmd=["sleep", "1599"], preexec_func=os.setsid, timeout=1
        )
        self.assertEqual(exit_code, TIMEOUT_EXIT_CODE)
        self.assertEqual(stdout.strip(), b"")
        self.assertEqual(stderr.strip(), b"")
        self.assertTrue(timed_out)

        # Verify there is no zombie process left laying around
        self.assertNoStrayProcessesLeft("sleep 1599")

    def test_run_command_timeout_no_shell_no_custom_kill_func_and_read_funcs(self):
        def mock_read_stdout(process_stdout, stdout_buffer):
            try:
                stdout_buffer.write(process_stdout.readline())
            except greenlet.GreenletExit:
                pass

        def mock_read_stderr(process_stderr, stderr_buffer):
            try:
                stderr_buffer.write(process_stderr.readline())
            except greenlet.GreenletExit:
                pass

        read_stdout_buffer = BytesIO()
        read_stderr_buffer = BytesIO()

        script_path = os.path.abspath(
            os.path.join(BASE_DIR, "../fixtures/print_to_stdout_stderr_sleep.sh")
        )

        exit_code, stdout, stderr, timed_out = run_command(
            cmd=[script_path],
            preexec_func=os.setsid,
            timeout=3,
            read_stdout_func=mock_read_stdout,
            read_stderr_func=mock_read_stderr,
            read_stdout_buffer=read_stdout_buffer,
            read_stderr_buffer=read_stderr_buffer,
        )
        self.assertEqual(exit_code, TIMEOUT_EXIT_CODE)
        self.assertEqual(stdout.strip(), b"pre sleep")
        self.assertEqual(stderr.strip(), b"pre sleep stderr")
        self.assertTrue(timed_out)

        # Only initial produced line should be read
        self.assertEqual(read_stdout_buffer.getvalue().strip(), b"pre sleep")
        self.assertEqual(read_stderr_buffer.getvalue().strip(), b"pre sleep stderr")

        # Verify there is no zombie process left laying around
        self.assertNoStrayProcessesLeft("print_to_stdout_stderr_sleep")

    def assertNoStrayProcessesLeft(self, grep_string: str) -> None:
        """
        Assert that there are no stray / zombie processes left with the provided command line
        string.
        """
        exit_code, stdout, stderr, timed_out = run_command(
            cmd="ps aux | grep %s | grep -v grep" % (quote_unix(grep_string)),
            shell=True,
        )

        if stdout.strip() != b"" and stderr.strip() != b"":
            raise AssertionError(
                "Expected no stray processes, but found Some. stdout: %s, stderr: %s"
                % (stdout, stderr)
            )
