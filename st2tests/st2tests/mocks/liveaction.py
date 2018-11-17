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

from __future__ import absolute_import, print_function
import eventlet
import traceback

from st2actions import worker
from st2actions.scheduler import entrypoint, handler
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.execution_queue import ExecutionQueue

__all__ = [
    'MockLiveActionPublisher',
    'MockLiveActionPublisherNonBlocking',
    'setup',
    'teardown'
]


SCHEDULER_HANDLER = None
ENTRYPOINT = None


def setup(no_start_handler=False):
    global SCHEDULER_HANDLER
    global ENTRYPOINT

    SCHEDULER_HANDLER = handler.get_handler()

    if not no_start_handler:
        SCHEDULER_HANDLER.start()

    ENTRYPOINT = entrypoint.get_scheduler_entrypoint()


def teardown(no_start_handler=False):
    global SCHEDULER_HANDLER
    global ENTRYPOINT

    if not no_start_handler and SCHEDULER_HANDLER:
        SCHEDULER_HANDLER.shutdown()
    for execution in ExecutionQueue.get_all():
        ExecutionQueue.delete(execution)

    SCHEDULER_HANDLER = None
    ENTRYPOINT = None


class MockLiveActionPublisher(object):

    @classmethod
    def publish_create(cls, payload):
        try:
            if isinstance(payload, LiveActionDB):
                setup(True)
                ex_req = ENTRYPOINT.process(payload)
                SCHEDULER_HANDLER._handle_execution(ex_req)
                teardown(True)
        except Exception:
            traceback.print_exc()
            print(payload)

    @classmethod
    def publish_state(cls, payload, state):
        try:
            if isinstance(payload, LiveActionDB):
                if state == action_constants.LIVEACTION_STATUS_REQUESTED:
                    setup(True)
                    ex_req = ENTRYPOINT.process(payload)
                    SCHEDULER_HANDLER._handle_execution(ex_req)
                    teardown(True)
                else:
                    worker.get_worker().process(payload)
        except Exception:
            traceback.print_exc()
            print(payload)


class MockLiveActionPublisherNonBlocking(object):
    threads = []

    @classmethod
    def publish_create(cls, payload):
        try:
            if isinstance(payload, LiveActionDB):
                thread = eventlet.spawn(ENTRYPOINT.process, payload)
                cls.threads.append(thread)
        except Exception:
            traceback.print_exc()
            print(payload)

    @classmethod
    def publish_state(cls, payload, state):
        try:
            if isinstance(payload, LiveActionDB):
                if state == action_constants.LIVEACTION_STATUS_REQUESTED:
                    thread = eventlet.spawn(ENTRYPOINT.process, payload)
                    cls.threads.append(thread)
                else:
                    thread = eventlet.spawn(worker.get_worker().process, payload)
                    cls.threads.append(thread)
        except Exception:
            traceback.print_exc()
            print(payload)

    @classmethod
    def wait_all(cls):
        for thread in cls.threads:
            try:
                thread.wait()
            except Exception as e:
                print(str(e))
            finally:
                cls.threads.remove(thread)
