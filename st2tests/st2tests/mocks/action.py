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
Mock classes for use in pack testing.
"""

from logging import RootLogger

from mock import Mock

from st2actions.runners.python_action_wrapper import ActionService
from st2tests.mocks.datastore import MockDatastoreService

__all__ = [
    'MockActionWrapper',
    'MockActionService'
]


class MockActionWrapper(object):
    def __init__(self, pack, class_name):
        self._pack = pack
        self._class_name = class_name


class MockActionService(ActionService):
    """
    Mock ActionService for use in testing.
    """

    def __init__(self, action_wrapper):
        self._action_wrapper = action_wrapper

        # Holds a mock logger instance
        # We use a Mock class so use can assert logger was called with particular arguments
        self._logger = Mock(spec=RootLogger)

        self._datastore_service = MockDatastoreService(logger=self._logger,
                                                       pack_name=self._action_wrapper._pack,
                                                       class_name=self._action_wrapper._class_name,
                                                       api_username='action_service')
