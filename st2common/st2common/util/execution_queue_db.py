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

from mongoengine import ValidationError

from st2common import log as logging
from st2common.util import date
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.execution_queue import ExecutionQueue
from st2common.models.db.execution_queue import ExecutionQueueDB

LOG = logging.getLogger(__name__)


__all__ = [
    'get_execution_request_by_id',
    'pop_next_execution'
]


def get_execution_request_by_id(action_id):
    """
        Get Action by id.

        On error, raise StackStormDBObjectNotFoundError
    """
    action = None

    try:
        action = ExecutionQueue.get_by_id(action_id)
    except (ValueError, ValidationError) as e:
        LOG.warning('Database lookup for action with id="%s" resulted in '
                    'exception: %s', action_id, e)
        raise StackStormDBObjectNotFoundError('Unable to find action with '
                                              'id="%s"' % action_id)

    return action


def create_execution_request_from_liveaction(liveaction, delay=None,
                                             priority=None, affinity=None):
    """
        Create execution request from liveaction.
    """
    execution_request = ExecutionQueueDB()
    execution_request.liveaction = liveaction.to_serializable_dict()
    execution_request.start_timestamp = date.append_milliseconds_to_time(
        liveaction.start_timestamp,
        delay
    )
    execution_request.delay = delay
    execution_request.priority = priority
    execution_request.affinity = affinity

    return execution_request


def pop_next_execution():
    """
        Sort executions by fifo and priority and get the latest, highest priority
        item from the queue and pop it off.
    """
    query = {
        "start_timestamp__lte": date.get_datetime_utc_now(),
        "order_by": [
            "-priority",
            "start_timestamp",
            "delay",
        ]
    }

    next_execution = ExecutionQueue.query(**query)
    if next_execution:
        next_execution = next_execution[0]
        ExecutionQueue.delete(next_execution)
        return next_execution

    return None
