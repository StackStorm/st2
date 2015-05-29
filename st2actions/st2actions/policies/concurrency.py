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

from st2common.constants import action as action_constants
from st2common import log as logging
from st2common.persistence import action as action_access
from st2common.policies import base
from st2common.services import coordination
from st2common.services import executions
from st2common.util import action_db as action_utils


LOG = logging.getLogger(__name__)


class ConcurrencyApplicator(base.ResourcePolicyApplicator):

    def __init__(self, policy_ref, policy_type, *args, **kwargs):
        super(ConcurrencyApplicator, self).__init__(policy_ref, policy_type, *args, **kwargs)
        self.coordinator = coordination.get_coordinator()
        self.threshold = kwargs.get('threshold', 0)

    def _apply_before(self, target):
        # Get the count of scheduled instances of the action.
        scheduled = action_access.LiveAction.count(
            action=target.action, status=action_constants.LIVEACTION_STATUS_SCHEDULED)

        # Get the count of running instances of the action.
        running = action_access.LiveAction.count(
            action=target.action, status=action_constants.LIVEACTION_STATUS_RUNNING)

        count = scheduled + running

        # Mark the execution as scheduled if threshold is not reached or delayed otherwise.
        if count < self.threshold:
            LOG.debug('There are %s instances of %s in scheduled or running status. '
                      'Threshold of %s is not reached. Action execution will be scheduled.',
                      count, target.action, self._policy_ref)
            status = action_constants.LIVEACTION_STATUS_SCHEDULED
        else:
            LOG.debug('There are %s instances of %s in scheduled or running status. '
                      'Threshold of %s is reached. Action execution will be delayed.',
                      count, target.action, self._policy_ref)
            status = action_constants.LIVEACTION_STATUS_DELAYED

        # Update the status in the database but do not publish.
        target = action_utils.update_liveaction_status(
            status=status,
            liveaction_id=target.id,
            publish=False)

        action_execution_db = executions.update_execution(target)

        extra = {'action_execution_db': action_execution_db, 'liveaction_db': target}
        LOG.audit('The status of action execution (id=%s) / live action (id=%s) '
                  'is changed from %s to %s.', action_execution_db.id, target.id,
                  target.status, status, extra=extra)

        LOG.info('The status of action execution (id=%s) / live action (id=%s) '
                 'is changed from %s to %s.', action_execution_db.id, target.id,
                 target.status, status)

        return target

    def apply_before(self, target):
        # Exit if target not in schedulable state.
        if target.status != action_constants.LIVEACTION_STATUS_REQUESTED:
            LOG.debug('The live action is not schedulable therefore the policy '
                      '"%s" cannot be applied. %s', self._policy_ref, target)
            return target

        # Warn users that the coordination service is not configured.
        if not coordination.configured():
            LOG.warn('Coordination service is not configured. Policy enforcement is best effort.')

        # Acquire a distributed lock before querying the database to make sure that only one
        # scheduler is scheduling execution for this action. Even if the coordination service
        # is not configured, the fake driver using zake or the file driver can still acquire
        # a lock for the local process or server respectively.
        lock_uid = '[%s][%s]' % (self._policy_type, target.action)
        LOG.debug('%s is attempting to acquire lock "%s".', self.__class__.__name__, lock_uid)
        with self.coordinator.get_lock(lock_uid):
            target = self._apply_before(target)

        return target

    def apply_after(self, target):
        return target
