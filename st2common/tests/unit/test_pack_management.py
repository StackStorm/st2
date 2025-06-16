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

import os
import sys

import unittest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACK_ACTIONS_DIR = os.path.join(BASE_DIR, "../../../contrib/packs/actions")
PACK_ACTIONS_DIR = os.path.abspath(PACK_ACTIONS_DIR)

sys.path.insert(0, PACK_ACTIONS_DIR)

from st2common.util.monkey_patch import use_select_poll_workaround

use_select_poll_workaround()

from st2common.util.pack_management import eval_repo_url

__all__ = ["InstallPackTestCase"]


class InstallPackTestCase(unittest.TestCase):
    def test_eval_repo(self):
        result = eval_repo_url("stackstorm/st2contrib")
        self.assertEqual(result, "https://github.com/stackstorm/st2contrib")

        result = eval_repo_url("git@github.com:StackStorm/st2contrib.git")
        self.assertEqual(result, "git@github.com:StackStorm/st2contrib.git")

        result = eval_repo_url("gitlab@gitlab.com:StackStorm/st2contrib.git")
        self.assertEqual(result, "gitlab@gitlab.com:StackStorm/st2contrib.git")

        repo_url = "https://github.com/StackStorm/st2contrib.git"
        result = eval_repo_url(repo_url)
        self.assertEqual(result, repo_url)

        repo_url = "https://git-wip-us.apache.org/repos/asf/libcloud.git"
        result = eval_repo_url(repo_url)
        self.assertEqual(result, repo_url)
