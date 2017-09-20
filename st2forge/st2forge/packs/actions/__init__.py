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

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class Action(object):
    """
    Base action class other Python actions should inherit from.
    """

    description = None

    def __init__(self, config=None, action_service=None, logger=None):
        """
        :param config: Action config.
        :type config: ``dict``

        :param action_service: ActionService object.
        :type action_service: :class:`ActionService`

        :param logger: Logger object.
        :type logger: :class:`Logger`
        """
        self.config = config or {}
        self.action_service = action_service
        self.logger = logger

    @abc.abstractmethod
    def run(self, **kwargs):
        pass
