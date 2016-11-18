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

"""
Test case which tests that Python runner action wrapper finishes in <= 200ms. If the process takes
more time to finish, this means it probably directly or in-directly imports some modules which have
side affects and are very slow to import.

Examples of such modules include:
* jsonschema
* pecan
* jinja2
* kombu
* mongoengine

If the tests fail, look at the recent changes and analyze the import graph using the following
command: "profimp "from st2common.runners import python_action_wrapper" --html > report.html"
"""

import os

import unittest2
from distutils.spawn import find_executable

from st2common.util.shell import run_command

__all__ = [
    'PythonRunnerActionWrapperProcessTestCase'
]

# Maximum limit for the process wrapper script execution time (in seconds)
WRAPPER_PROCESS_RUN_TIME_UPPER_LIMIT = 0.20

ASSERTION_ERROR_MESSAGE = ("""
Python wrapper process script took more than %s seconds to execute (%s). This most likely means
that a direct or in-direct import of a module which takes a long time to load has been added (e.g.
jsonschema, pecan, kombu, etc).

Please review recently changed and added code for potential slow import issues and refactor /
re-organize code if possible.
""".strip())

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WRAPPER_SCRIPT_PATH = os.path.join(BASE_DIR, '../../st2common/runners/python_action_wrapper.py')
TIME_BINARY_PATH = find_executable('time')
TIME_BINARY_AVAILABLE = TIME_BINARY_PATH is not None


@unittest2.skipIf(not TIME_BINARY_PATH, 'time binary not available')
class PythonRunnerActionWrapperProcessTestCase(unittest2.TestCase):
    def test_process_wrapper_exits_in_reasonable_timeframe(self):
        _, _, stderr = run_command('%s -f "%%e" python %s --is-subprocess' %
                                   (TIME_BINARY_PATH, WRAPPER_SCRIPT_PATH), shell=True)

        stderr = stderr.strip().split('\n')[-1]

        run_time_seconds = float(stderr)
        assertion_msg = ASSERTION_ERROR_MESSAGE % (WRAPPER_PROCESS_RUN_TIME_UPPER_LIMIT,
                        run_time_seconds)
        self.assertTrue(run_time_seconds <= WRAPPER_PROCESS_RUN_TIME_UPPER_LIMIT, assertion_msg)
