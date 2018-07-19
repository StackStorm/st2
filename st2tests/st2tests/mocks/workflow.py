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

import eventlet
import traceback

from st2actions.workflows import workflows
from st2common.models.db import workflow as wf_ex_db


__all__ = [
    'MockWorkflowExecutionPublisher'
]


class MockWorkflowExecutionPublisher(object):

    @classmethod
    def publish_create(cls, payload):
        try:
            if isinstance(payload, wf_ex_db.WorkflowExecutionDB):
                workflows.get_engine().process(payload)
        except Exception:
            traceback.print_exc()
            print(payload)

    @classmethod
    def publish_state(cls, payload, state):
        try:
            if isinstance(payload, wf_ex_db.WorkflowExecutionDB):
                workflows.get_engine().process(payload)
        except Exception:
            traceback.print_exc()
            print(payload)


class MockWorkflowExecutionPublisherNonBlocking(object):
    threads = []

    @classmethod
    def publish_create(cls, payload):
        try:
            if isinstance(payload, wf_ex_db.WorkflowExecutionDB):
                thread = eventlet.spawn(workflows.get_engine().process, payload)
                cls.threads.append(thread)
        except Exception:
            traceback.print_exc()
            print(payload)

    @classmethod
    def publish_state(cls, payload, state):
        try:
            if isinstance(payload, wf_ex_db.WorkflowExecutionDB):
                thread = eventlet.spawn(workflows.get_engine().process, payload)
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
