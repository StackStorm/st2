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

import traceback

import unittest2

from st2tests import config as test_config
test_config.parse_args()

from st2actions import worker
from st2actions import scheduler
from st2actions.notifier import notifier
from st2common.constants import action as action_constants
from st2common.constants.system import AUTH_TOKEN_ENV_VARIABLE_NAME
from st2common.models.db.liveaction import LiveActionDB
from st2common.util.api import get_full_public_api_url
from st2common.constants.runners import COMMON_ACTION_ENV_VARIABLES

__all__ = [
    'RunnerTestCase',
    'MockLiveActionPublisher'
]


class RunnerTestCase(unittest2.TestCase):
    def assertCommonSt2EnvVarsAvailableInEnv(self, env):
        """
        Method which asserts that the common ST2 environment variables are present in the provided
        environment.
        """
        for var_name in COMMON_ACTION_ENV_VARIABLES:
            self.assertTrue(var_name in env)

        self.assertEqual(env['ST2_ACTION_API_URL'], get_full_public_api_url())
        self.assertTrue(env[AUTH_TOKEN_ENV_VARIABLE_NAME] is not None)


class MockLiveActionPublisher(object):

    @classmethod
    def publish_create(cls, payload):
        try:
            if isinstance(payload, LiveActionDB):
                scheduler.get_scheduler().process(payload)
        except Exception:
            traceback.print_exc()
            print(payload)

    @classmethod
    def publish_state(cls, payload, state):
        try:
            if isinstance(payload, LiveActionDB):
                if state == action_constants.LIVEACTION_STATUS_REQUESTED:
                    scheduler.get_scheduler().process(payload)
                else:
                    worker.get_worker().process(payload)
        except Exception:
            traceback.print_exc()
            print(payload)

    @classmethod
    def publish_update(cls, payload):
        try:
            if isinstance(payload, LiveActionDB):
                notifier.get_notifier().process(payload)
        except Exception:
            traceback.print_exc()
            print(payload)
