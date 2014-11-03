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

# XXX: FabricRunner import depends on config being setup.
import st2tests.config as tests_config
tests_config.parse_args()

from unittest2 import TestCase

from st2actions.runners.fabricrunner import FabricRunner
from st2common.constants.action import ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_FAILED


class TestFabricRunnerResultStatus(TestCase):

    def test_pf_ok_all_success(self):
        result = {
            '1': {'succeeded': True},
            '2': {'succeeded': True},
            '3': {'succeeded': True},
        }
        self.assertEquals(ACTIONEXEC_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, True))

    def test_pf_ok_some_success(self):
        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': True},
            '3': {'succeeded': False},
        }
        self.assertEquals(ACTIONEXEC_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, True))

        result = {
            '1': {'succeeded': True},
            '2': {'succeeded': False},
            '3': {'succeeded': False},
        }
        self.assertEquals(ACTIONEXEC_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, True))

        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': False},
            '3': {'succeeded': True},
        }
        self.assertEquals(ACTIONEXEC_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, True))

    def test_pf_ok_all_fail(self):
        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': False},
            '3': {'succeeded': False},
        }
        self.assertEquals(ACTIONEXEC_STATUS_FAILED,
                          FabricRunner._get_result_status(result, True))

    def test_pf_not_ok_all_success(self):
        result = {
            '1': {'succeeded': True},
            '2': {'succeeded': True},
            '3': {'succeeded': True},
        }
        self.assertEquals(ACTIONEXEC_STATUS_SUCCEEDED,
                          FabricRunner._get_result_status(result, False))

    def test_pf_not_ok_some_success(self):
        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': True},
            '3': {'succeeded': False},
        }
        self.assertEquals(ACTIONEXEC_STATUS_FAILED,
                          FabricRunner._get_result_status(result, False))

        result = {
            '1': {'succeeded': True},
            '2': {'succeeded': False},
            '3': {'succeeded': False},
        }
        self.assertEquals(ACTIONEXEC_STATUS_FAILED,
                          FabricRunner._get_result_status(result, False))

        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': False},
            '3': {'succeeded': True},
        }
        self.assertEquals(ACTIONEXEC_STATUS_FAILED,
                          FabricRunner._get_result_status(result, False))

    def test_pf_not_ok_all_fail(self):
        result = {
            '1': {'succeeded': False},
            '2': {'succeeded': False},
            '3': {'succeeded': False},
        }
        self.assertEquals(ACTIONEXEC_STATUS_FAILED,
                          FabricRunner._get_result_status(result, False))
