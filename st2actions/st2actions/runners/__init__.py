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

import six
import abc

from st2actions import handlers
from st2common import log as logging


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class ActionRunner(object):
    """
        The interface that must be implemented by each StackStorm
        Action Runner implementation.
    """

    def __init__(self, id):
        """
        :param id: Runner id.
        :type id: ``str``
        """
        self.runner_id = id

        self.container_service = None
        self.runner_parameters = None
        self.action = None
        self.action_name = None
        self.action_execution_id = None
        self.entry_point = None
        self.libs_dir_path = None
        self.context = None
        self.callback = None
        self.auth_token = None

    @abc.abstractmethod
    def pre_run(self):
        raise NotImplementedError()

    # Run will need to take an action argument
    # Run may need result data argument
    @abc.abstractmethod
    def run(self, action_parameters):
        raise NotImplementedError()

    def post_run(self):
        if self.callback and not (set(['url', 'source']) - set(self.callback.keys())):
            handler = handlers.get_handler(self.callback['source'])
            handler.callback(self.callback['url'],
                             self.context,
                             self.container_service.get_status(),
                             self.container_service.get_result())

    def __str__(self):
        attrs = ', '.join(['%s=%s' % (k, v) for k, v in six.iteritems(self.__dict__)])
        return '%s@%s(%s)' % (self.__class__.__name__, str(id(self)), attrs)
