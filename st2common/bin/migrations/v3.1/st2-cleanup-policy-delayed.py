#!/usr/bin/env python

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

from __future__ import absolute_import

import sys

from st2common import config
from st2common.constants import action as action_constants
from st2common.exceptions import db as db_exc
from st2common.persistence.execution_queue import ActionExecutionSchedulingQueue
from st2common.persistence.liveaction import LiveAction
from st2common.service_setup import db_setup
from st2common.service_setup import db_teardown
from st2common.services import action as action_service
from st2common.services import executions as execution_service


def reset_policy_delayed():
    """
    Clean up any action execution in the deprecated policy-delayed status. Associated
    entries in the scheduling queue will be removed and the action execution will be
    moved back into requested status.
    """

    policy_delayed_liveaction_dbs = LiveAction.query(status='policy-delayed') or []

    for liveaction_db in policy_delayed_liveaction_dbs:
        ex_que_qry = {'liveaction_id': str(liveaction_db.id), 'handling': False}
        execution_queue_item_dbs = ActionExecutionSchedulingQueue.query(**ex_que_qry) or []

        for execution_queue_item_db in execution_queue_item_dbs:
            # Mark the entry in the scheduling queue for handling.
            try:
                execution_queue_item_db.handling = True
                execution_queue_item_db = ActionExecutionSchedulingQueue.add_or_update(
                    execution_queue_item_db, publish=False)
            except db_exc.StackStormDBObjectWriteConflictError:
                raise Exception(
                    '[%s] Item "%s" is currently being processed by another scheduler or script.' %
                    (execution_queue_item_db.action_execution_id, str(execution_queue_item_db.id))
                )

            # Delete the entry from the scheduling queue.
            print(
                '[%s] Removing policy-delayed entry "%s" from the scheduling queue.' %
                (execution_queue_item_db.action_execution_id, str(execution_queue_item_db.id))
            )

            ActionExecutionSchedulingQueue.delete(execution_queue_item_db)

            # Update the status of the liveaction and execution to requested.
            print(
                '[%s] Removing policy-delayed entry "%s" from the scheduling queue.' %
                (execution_queue_item_db.action_execution_id, str(execution_queue_item_db.id))
            )

            liveaction_db = action_service.update_status(
                liveaction_db, action_constants.LIVEACTION_STATUS_REQUESTED)

            execution_service.update_execution(liveaction_db)


def main():
    config.parse_args()

    # Connect to db.
    db_setup()

    try:
        reset_policy_delayed()
        print('SUCCESS: Completed clean up of executions with deprecated policy-delayed status.')
        exit_code = 0
    except Exception as e:
        print(
            'ABORTED: Clean up of executions with deprecated policy-delayed status aborted on '
            'first failure. %s' % e.message
        )
        exit_code = 1

    # Disconnect from db.
    db_teardown()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
