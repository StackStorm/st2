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

from __future__ import absolute_import

import logging

from st2common.models.db.executionstate import ActionExecutionStateDB
from st2common.persistence.executionstate import ActionExecutionState


LOG = logging.getLogger(__name__)


def setup_query(liveaction_id, runnertype_db, query_context):
    if not getattr(runnertype_db, 'query_module', None):
        raise Exception('The runner "%s" does not have a query module.' % runnertype_db.name)

    state_db = ActionExecutionStateDB(
        execution_id=liveaction_id,
        query_module=runnertype_db.query_module,
        query_context=query_context
    )

    ActionExecutionState.add_or_update(state_db)


def remove_query(liveaction_id):
    state_db = ActionExecutionState.query(execution_id=liveaction_id)

    if not state_db:
        return False

    ActionExecutionState.delete(state_db, publish=False, dispatch_trigger=False)

    return True
