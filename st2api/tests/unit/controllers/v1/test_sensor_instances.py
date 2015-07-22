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

import six
from tests import FunctionalTest

http_client = six.moves.http_client


class SensorInstanceControllerTestCase(FunctionalTest):
    def test_get_all(self):
        resp = self.app.get('/v1/sensorinstances')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 0)

    def test_get_one_doesnt_exist(self):
        resp = self.app.get('/v1/sensorinstances/1', expect_errors=True)
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)
