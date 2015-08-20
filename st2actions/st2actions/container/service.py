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

from st2common.content import utils
from st2common import log as logging

LOG = logging.getLogger(__name__)
STDOUT = 'stdout'
STDERR = 'stderr'


class RunnerContainerService(object):
    """
        The RunnerContainerService class implements the interface
        that ActionRunner implementations use to access services
        provided by the Action Runner Container.
    """

    def __init__(self):
        self._status = None
        self._result = None
        self._payload = {}

    def report_payload(self, name, value):
        self._payload[name] = value

    def get_logger(self, name):
        logging.getLogger(__name__ + '.' + name)

    @staticmethod
    def get_pack_base_path(pack_name):
        return utils.get_pack_base_path(pack_name)

    @staticmethod
    def get_entry_point_abs_path(pack=None, entry_point=None):
        return utils.get_entry_point_abs_path(pack, entry_point)

    @staticmethod
    def get_action_libs_abs_path(pack=None, entry_point=None):
        return utils.get_action_libs_abs_path(pack, entry_point)

    def __str__(self):
        result = []
        result.append('RunnerContainerService@')
        result.append(str(id(self)))
        result.append('(')
        result.append('_result="%s", ' % self._result)
        result.append('_payload="%s", ' % self._payload)
        result.append(')')
        return ''.join(result)
