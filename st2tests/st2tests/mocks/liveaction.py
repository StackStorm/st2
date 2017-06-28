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

import eventlet
import traceback

from st2actions import worker
from st2actions import scheduler
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB

__all__ = [
    'MockLiveActionPublisher'
]


class MockLiveActionPublisher(object):

    @classmethod
    def publish_create(cls, payload):
        try:
            if isinstance(payload, LiveActionDB):
                scheduler.get_scheduler().process(payload)
        except Exception:
            traceback.print_exc()
            print(payload)

    @classmethod
    def publish_state(cls, payload, state):
        try:
            if isinstance(payload, LiveActionDB):
                if state == action_constants.LIVEACTION_STATUS_REQUESTED:
                    scheduler.get_scheduler().process(payload)
                else:
                    worker.get_worker().process(payload)
        except Exception:
            traceback.print_exc()
            print(payload)


class MockLiveActionPublisherNonBlocking(object):

    @classmethod
    def publish_create(cls, payload):
        try:
            if isinstance(payload, LiveActionDB):
                eventlet.spawn(scheduler.get_scheduler().process, payload)
        except Exception:
            traceback.print_exc()
            print(payload)

    @classmethod
    def publish_state(cls, payload, state):
        try:
            if isinstance(payload, LiveActionDB):
                if state == action_constants.LIVEACTION_STATUS_REQUESTED:
                    eventlet.spawn(scheduler.get_scheduler().process, payload)
                else:
                    eventlet.spawn(worker.get_worker().process, payload)
        except Exception:
            traceback.print_exc()
            print(payload)
