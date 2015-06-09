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

__all__ = [
    'ACTION_NAME',
    'ACTION_ID',

    'LIBS_DIR',

    'LIVEACTION_STATUS_REQUESTED',
    'LIVEACTION_STATUS_SCHEDULED',
    'LIVEACTION_STATUS_DELAYED',
    'LIVEACTION_STATUS_RUNNING',
    'LIVEACTION_STATUS_SUCCEEDED',
    'LIVEACTION_STATUS_FAILED',
    'LIVEACTION_STATUS_CANCELED',

    'LIVEACTION_STATUSES',

    'ACTION_OUTPUT_RESULT_DELIMITER'
]


ACTION_NAME = 'name'
ACTION_ID = 'id'
ACTION_PACK = 'pack'

LIBS_DIR = 'lib'

LIVEACTION_STATUS_REQUESTED = 'requested'
LIVEACTION_STATUS_SCHEDULED = 'scheduled'
LIVEACTION_STATUS_DELAYED = 'delayed'
LIVEACTION_STATUS_RUNNING = 'running'
LIVEACTION_STATUS_SUCCEEDED = 'succeeded'
LIVEACTION_STATUS_FAILED = 'failed'
LIVEACTION_STATUS_CANCELED = 'canceled'

LIVEACTION_STATUSES = [
    LIVEACTION_STATUS_REQUESTED,
    LIVEACTION_STATUS_SCHEDULED,
    LIVEACTION_STATUS_DELAYED,
    LIVEACTION_STATUS_RUNNING,
    LIVEACTION_STATUS_SUCCEEDED,
    LIVEACTION_STATUS_FAILED,
    LIVEACTION_STATUS_CANCELED
]

ACTION_OUTPUT_RESULT_DELIMITER = '%%%%%~=~=~=************=~=~=~%%%%'

RUNNABLE_STATES = [
    LIVEACTION_STATUS_REQUESTED,
    LIVEACTION_STATUS_SCHEDULED
]

CANCELABLE_STATES = [
    LIVEACTION_STATUS_REQUESTED,
    LIVEACTION_STATUS_SCHEDULED,
    LIVEACTION_STATUS_DELAYED,
    LIVEACTION_STATUS_RUNNING
]

COMPLETED_STATES = [
    LIVEACTION_STATUS_SUCCEEDED,
    LIVEACTION_STATUS_FAILED,
    LIVEACTION_STATUS_CANCELED
]
