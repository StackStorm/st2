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

from st2common.runners.base import get_runner
from st2common.exceptions.actionrunner import ActionRunnerCreateError

from st2tests.base import DbTestCase


class RunnersLoaderUtilsTestCase(DbTestCase):
    def test_get_runner_success(self):
        runner = get_runner("local-shell-cmd")
        self.assertTrue(runner)
        self.assertEqual(runner.__class__.__name__, "LocalShellCommandRunner")

    def test_get_runner_failure_not_found(self):
        expected_msg = "Failed to find runner invalid-name-not-found.*"
        self.assertRaisesRegex(
            ActionRunnerCreateError, expected_msg, get_runner, "invalid-name-not-found"
        )
