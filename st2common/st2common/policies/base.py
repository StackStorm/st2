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
class ResourcePolicyApplicator(object):
    """Abstract policy application class."""

    def __init__(self, policy_ref, policy_type, *args, **kwargs):
        self._policy_ref = policy_ref
        self._policy_type = policy_type

    def apply_before(self, target):
        """
        Apply the policy before the target do work.

        :param target: The instance of the resource being affected by this policy.
        :type target: ``object``

        :rtype: ``object``
        """
        return target

    def apply_after(self, target):
        """
        Apply the policy after the target does work.

        :param target: The instance of the resource being affected by this policy.
        :type target: ``object``

        :rtype: ``object``
        """
        return target


def get_driver(policy_ref, policy_type, **parameters):
    policy_type_db = policy_access.PolicyType.get_by_ref(policy_type)
    module = importlib.import_module(policy_type_db.module, package=None)
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, ResourcePolicyApplicator):
            return obj(policy_ref, policy_type, **parameters)
