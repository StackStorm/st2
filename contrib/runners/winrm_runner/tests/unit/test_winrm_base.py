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

from st2common.runners.base import ActionRunner
from unittest2 import TestCase
from winrm_runner.winrm_base import WinRmBaseRunner, WinRmRunnerTimoutError


class WinRmBaseTestCase(TestCase):

    def test_win_rm_runner_timout_error(self):
        error = WinRmRunnerTimoutError('test_response')
        self.assertIsInstance(error, Exception)
        self.assertEquals(error.response, 'test_response')
        with self.assertRaises(WinRmRunnerTimoutError):
            raise WinRmRunnerTimoutError('test raising')

    def test_init(self)
        runner = WinRmBaseRunner('abcdef'):
        self.assertIsInstance(ActionRunner)
        self.assertEquals(runner.runner_id, "abcdef")
