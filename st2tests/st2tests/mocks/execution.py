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

from st2actions.notifier import notifier
from st2common.models.db.execution import ActionExecutionDB


__all__ = [
    'MockExecutionPublisher'
]


class MockExecutionPublisher(object):

    @classmethod
    def publish_update(cls, payload):
        try:
            if isinstance(payload, ActionExecutionDB):
                notifier.get_notifier().process(payload)
        except Exception:
            traceback.print_exc()
            print(payload)


class MockExecutionPublisherNonBlocking(object):

    @classmethod
    def publish_update(cls, payload):
        try:
            if isinstance(payload, ActionExecutionDB):
                eventlet.spawn(notifier.get_notifier().process, payload)
        except Exception:
            traceback.print_exc()
            print(payload)
