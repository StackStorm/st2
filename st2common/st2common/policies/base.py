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
from st2common.services import coordination

LOG = logging.getLogger(__name__)

__all__ = [
    'ResourcePolicyApplicator',
    'get_driver'
]


@six.add_metaclass(abc.ABCMeta)
class ResourcePolicyApplicator(object):
    """Abstract policy application class."""

    def __init__(self, policy_ref, policy_type):
        self._policy_ref = policy_ref
        self._policy_type = policy_type

    def apply_before(self, target):
        """
        Apply the policy before the target do work.

        :param target: The instance of the resource being affected by this policy.
        :type target: ``object``

        :rtype: ``object``
        """
        # Warn users that the coordination service is not configured
        if not coordination.configured():
            LOG.warn('Coordination service is not configured. Policy enforcement is best effort.')

        return target

    def apply_after(self, target):
        """
        Apply the policy after the target does work.

        :param target: The instance of the resource being affected by this policy.
        :type target: ``object``

        :rtype: ``object``
        """
        # Warn users that the coordination service is not configured
        if not coordination.configured():
            LOG.warn('Coordination service is not configured. Policy enforcement is best effort.')

        return target

    def _get_lock_name(self, values):
        """
        Return a safe string which can be used as a lock name.

        :param values: Dictionary with values to use in the lock name.
        :type values: ``dict``

        :rtype: ``st``
        """
        lock_uid = []

        for key, value in six.iteritems(values):
            lock_uid.append('%s=%s' % (key, value))

        lock_uid = ','.join(lock_uid)
        return lock_uid


def get_driver(policy_ref, policy_type, **parameters):
    policy_type_db = policy_access.PolicyType.get_by_ref(policy_type)
    module = importlib.import_module(policy_type_db.module, package=None)

    for name, obj in inspect.getmembers(module, predicate=inspect.isclass):
        if obj.__module__ != module.__name__:
            # Ignore classes which are just imported, but not defined in the module we are
            # interested in
            continue

        if (issubclass(obj, ResourcePolicyApplicator) and not obj.__name__.startswith('Base')):
            return obj(policy_ref, policy_type, **parameters)
