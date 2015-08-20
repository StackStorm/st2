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

from tests import FunctionalTest


class TestRunnerTypesController(FunctionalTest):

    def test_get_one(self):
        resp = self.app.get('/v1/runnertypes')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 0, '/v1/runnertypes did not return correct runnertypes.')
        runnertype_id = TestRunnerTypesController.__get_runnertype_id(resp.json[0])
        resp = self.app.get('/v1/runnertypes/%s' % runnertype_id)
        retrieved_id = TestRunnerTypesController.__get_runnertype_id(resp.json)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(retrieved_id, runnertype_id,
                         '/v1/runnertypes returned incorrect runnertype.')

    def test_get_all(self):
        resp = self.app.get('/v1/runnertypes')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 0, '/v1/runnertypes did not return correct runnertypes.')

    def test_get_one_fail(self):
        resp = self.app.get('/v1/runnertypes/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    @staticmethod
    def __get_runnertype_id(resp_json):
        return resp_json['id']
