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

import mock
import pecan

from st2api.controllers.v1 import stream
from st2api import listener
from tests import FunctionalTest


@mock.patch.object(pecan, 'request', type('request', (object,), {'environ': {}}))
@mock.patch.object(pecan, 'response', mock.MagicMock())
class TestStreamController(FunctionalTest):

    @mock.patch.object(stream, 'format', mock.Mock())
    @mock.patch.object(listener, 'get_listener', mock.Mock())
    def test_get_all(self):
        resp = stream.StreamController().get_all()
        self.assertIsInstance(resp._app_iter, mock.Mock)
        self.assertEqual(resp._status, '200 OK')
        self.assertIn(('Content-Type', 'text/event-stream; charset=UTF-8'), resp._headerlist)
