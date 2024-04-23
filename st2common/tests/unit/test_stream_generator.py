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

import mock
import unittest

from st2common.stream import listener


class MockBody(object):
    def __init__(self, id):
        self.id = id
        self.status = "succeeded"


INCLUDE = "test"
END_EVENT = "test_end_event"
END_ID = "test_end_id"
EVENTS = [(INCLUDE, MockBody("notend")), (END_EVENT, MockBody(END_ID))]


class MockQueue:
    def __init__(self):
        self.items = EVENTS

    def get(self, *args, **kwargs):
        if len(self.items) > 0:
            return self.items.pop(0)
        return None

    def put(self, event):
        self.items.append(event)


class MockListener(listener.BaseListener):
    def __init__(self, *args, **kwargs):
        super(MockListener, self).__init__(*args, **kwargs)

    def get_consumers(self, consumer, channel):
        pass


class TestStream(unittest.TestCase):
    @mock.patch("st2common.stream.listener.BaseListener._get_action_ref_for_body")
    @mock.patch("eventlet.Queue")
    def test_generator(self, mock_queue, get_action_ref_for_body):
        get_action_ref_for_body.return_value = None
        mock_queue.return_value = MockQueue()
        mock_consumer = MockListener(connection=None)
        mock_consumer._stopped = False
        app_iter = mock_consumer.generator(
            events=INCLUDE,
            end_event=END_EVENT,
            end_statuses=["succeeded"],
            end_execution_id=END_ID,
        )
        events = EVENTS.append("")
        for index, val in enumerate(app_iter):
            self.assertEquals(val, events[index])
