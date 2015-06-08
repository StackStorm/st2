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

import os
import sys

import unittest2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACK_ACTIONS_DIR = os.path.join(BASE_DIR, '../../../contrib/packs/actions')
PACK_ACTIONS_DIR = os.path.abspath(PACK_ACTIONS_DIR)

sys.path.insert(0, PACK_ACTIONS_DIR)

from pack_mgmt.download import InstallGitRepoAction


class InstallPackTestCase(unittest2.TestCase):
    def test_eval_subtree(self):
        # TODO: Check for OR
        result = InstallGitRepoAction._eval_subtree('stackstorm/st2contrib', False)
        self.assertTrue(result)
        result = InstallGitRepoAction._eval_subtree('stackstorm/st2incubator', False)
        self.assertTrue(result)

        result = InstallGitRepoAction._eval_subtree('stackstorm/foobar', False)
        self.assertFalse(result)

        result = InstallGitRepoAction._eval_subtree('kami/foobar', False)
        self.assertFalse(result)

        result = InstallGitRepoAction._eval_subtree('kami/foobar', True)
        self.assertTrue(result)

    def test_eval_repo(self):
        result = InstallGitRepoAction._eval_repo_url('stackstorm/st2contrib')
        self.assertEqual(result, 'https://github.com/stackstorm/st2contrib.git')

        result = InstallGitRepoAction._eval_repo_url('git@github.com:StackStorm/st2contrib.git')
        self.assertEqual(result, 'git@github.com:StackStorm/st2contrib.git')

        repo_url = 'https://github.com/StackStorm/st2contrib.git'
        result = InstallGitRepoAction._eval_repo_url(repo_url)
        self.assertEqual(result, repo_url)

        repo_url = 'https://git-wip-us.apache.org/repos/asf/libcloud.git'
        result = InstallGitRepoAction._eval_repo_url(repo_url)
        self.assertEqual(result, repo_url)
