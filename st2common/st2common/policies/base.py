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
import importlib
import inspect
import six

from st2common import log as logging
from st2common.persistence import policy as policy_access


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class ResourcePolicy(object):
    """Abstract policy class."""

    def __init__(self, *args, **kwargs):
        for k, v in six.iteritems(kwargs):
            setattr(self, k, v)

    @abc.abstractmethod
    def apply(self, target):
        """
        Apply the policy to the given target.

        :param target: The instance of the resource being affected by this policy.
        :type target: ``object``
        """
        pass


def get_driver(policy_type, **parameters):
    policy_type_db = policy_access.PolicyType.get_by_ref(policy_type)
    module = importlib.import_module(policy_type_db.module, package=None)
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, ResourcePolicy):
            return obj(**parameters)
