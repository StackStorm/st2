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

from st2actions.runners.utils import get_action_class_instance
from st2tests.mocks.action import MockActionWrapper
from st2tests.mocks.action import MockActionService
from st2tests.pack_resource import BasePackResourceTestCase

__all__ = [
    'BaseActionTestCase'
]


class BaseActionTestCase(BasePackResourceTestCase):
    """
    Base class for Python runner action tests.
    """

    action_cls = None

    def setUp(self):
        super(BaseActionTestCase, self).setUp()

        class_name = self.action_cls.__name__
        action_wrapper = MockActionWrapper(pack='tests', class_name=class_name)
        self.action_service = MockActionService(action_wrapper=action_wrapper)

    def get_action_instance(self, config=None):
        """
        Retrieve instance of the action class.
        """
        # pylint: disable=not-callable
        instance = get_action_class_instance(action_cls=self.action_cls,
                                             config=config,
                                             action_service=self.action_service)
        return instance
