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

from unittest2 import TestCase
from mock import Mock

from st2common.transport.consumers import ActionsQueueConsumer
from st2common.models.db.liveaction import LiveActionDB

from st2tests import config as test_config
test_config.parse_args()

__all__ = [
    'ActionsQueueConsumerTestCase'
]


class ActionsQueueConsumerTestCase(TestCase):
    def test_process_right_dispatcher_is_used(self):
        handler = Mock()
        handler.message_type = LiveActionDB
        consumer = ActionsQueueConsumer(connection=None, queues=None, handler=handler)

        # Non-workflow action
        consumer._workflows_dispatcher = Mock()
        consumer._actions_dispatcher = Mock()

        body = LiveActionDB(status='scheduled', action='core.local', action_is_workflow=False)
        message = Mock()
        consumer.process(body=body, message=message)

        self.assertEqual(consumer._workflows_dispatcher.dispatch.call_count, 0)
        self.assertEqual(consumer._actions_dispatcher.dispatch.call_count, 1)

        # Workflow action
        consumer._workflows_dispatcher = Mock()
        consumer._actions_dispatcher = Mock()

        body = LiveActionDB(status='scheduled', action='core.local', action_is_workflow=True)
        message = Mock()
        consumer.process(body=body, message=message)

        self.assertEqual(consumer._workflows_dispatcher.dispatch.call_count, 1)
        self.assertEqual(consumer._actions_dispatcher.dispatch.call_count, 0)
