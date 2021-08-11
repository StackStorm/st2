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

from st2tests.base import BaseActionTestCase

from pythonactions.isprime import PrimeCheckerAction


class PrimeCheckerActionTestCase(BaseActionTestCase):
    action_cls = PrimeCheckerAction

    def test_run(self):
        action = self.get_action_instance()
        result = action.run(value=1)
        self.assertFalse(result)

        result = action.run(value=3)
        self.assertTrue(result)
