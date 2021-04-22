# Copyright 2020 The StackStorm Authors.
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
from __future__ import print_function

import six
import eventlet
import traceback

from st2actions import worker
from st2actions.scheduler import entrypoint as scheduling
from st2actions.scheduler import handler as scheduling_queue
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB

__all__ = ["MockLiveActionPublisher", "MockLiveActionPublisherNonBlocking"]


class MockLiveActionPublisher(object):
    @classmethod
    def process(cls, payload):
        ex_req = scheduling.get_scheduler_entrypoint().process(payload)

        if ex_req is not None:
            scheduling_queue.get_handler()._handle_execution(ex_req)

    @classmethod
    def publish_create(cls, payload):
        # The scheduling entry point is only listening for status change and not on create.
        # Therefore, no additional processing is required here otherwise this will cause
        # duplicate processing in the unit tests.
        pass

    @classmethod
    def publish_state(cls, payload, state):
        try:
            if isinstance(payload, LiveActionDB):
                if state == action_constants.LIVEACTION_STATUS_REQUESTED:
                    cls.process(payload)
                else:
                    worker.get_worker().process(payload)
        except Exception:
            traceback.print_exc()
            print(payload)


class MockLiveActionPublisherNonBlocking(object):
    threads = []

    @classmethod
    def process(cls, payload):
        ex_req = scheduling.get_scheduler_entrypoint().process(payload)

        if ex_req is not None:
            scheduling_queue.get_handler()._handle_execution(ex_req)

    @classmethod
    def publish_create(cls, payload):
        # The scheduling entry point is only listening for status change and not on create.
        # Therefore, no additional processing is required here otherwise this will cause
        # duplicate processing in the unit tests.
        pass

    @classmethod
    def publish_state(cls, payload, state):
        try:
            if isinstance(payload, LiveActionDB):
                if state == action_constants.LIVEACTION_STATUS_REQUESTED:
                    thread = eventlet.spawn(cls.process, payload)
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
                print(six.text_type(e))
            finally:
                cls.threads.remove(thread)

        eventlet.sleep(0.1)


class MockLiveActionPublisherSchedulingQueueOnly(object):
    @classmethod
    def process(cls, payload):
        scheduling.get_scheduler_entrypoint().process(payload)

    @classmethod
    def publish_create(cls, payload):
        # The scheduling entry point is only listening for status change and not on create.
        # Therefore, no additional processing is required here otherwise this will cause
        # duplicate processing in the unit tests.
        pass

    @classmethod
    def publish_state(cls, payload, state):
        try:
            if isinstance(payload, LiveActionDB):
                if state == action_constants.LIVEACTION_STATUS_REQUESTED:
                    cls.process(payload)
                else:
                    worker.get_worker().process(payload)
        except Exception:
            traceback.print_exc()
            print(payload)
