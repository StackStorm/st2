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

from st2api.controllers.v1.runnertypes import RunnerTypesController

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

__all__ = [
    'RunnerTypesControllerTestCase'
]


class RunnerTypesControllerTestCase(FunctionalTest,
                                    APIControllerWithIncludeAndExcludeFilterTestCase):
    get_all_path = '/v1/runnertypes'
    controller_cls = RunnerTypesController
    include_attribute_field_name = 'runner_package'
    exclude_attribute_field_name = 'runner_module'
    test_exact_object_count = False  # runners are registered dynamically in base test class

    def test_get_one(self):
        resp = self.app.get('/v1/runnertypes')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 0, '/v1/runnertypes did not return correct runnertypes.')
        runnertype_id = RunnerTypesControllerTestCase.__get_runnertype_id(resp.json[0])
        resp = self.app.get('/v1/runnertypes/%s' % runnertype_id)
        retrieved_id = RunnerTypesControllerTestCase.__get_runnertype_id(resp.json)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(retrieved_id, runnertype_id,
                         '/v1/runnertypes returned incorrect runnertype.')

    def test_get_all(self):
        resp = self.app.get('/v1/runnertypes')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 0, '/v1/runnertypes did not return correct runnertypes.')

    def test_get_one_fail_doesnt_exist(self):
        resp = self.app.get('/v1/runnertypes/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    def test_put_disable_runner(self):
        runnertype_id = 'action-chain'
        resp = self.app.get('/v1/runnertypes/%s' % runnertype_id)
        self.assertTrue(resp.json['enabled'])

        # Disable the runner
        update_input = resp.json
        update_input['enabled'] = False
        update_input['name'] = 'foobar'

        put_resp = self.__do_put(runnertype_id, update_input)
        self.assertFalse(put_resp.json['enabled'])

        # Verify that the name hasn't been updated - we only allow updating
        # enabled attribute on the runner
        self.assertEqual(put_resp.json['name'], 'action-chain')

        # Enable the runner
        update_input = resp.json
        update_input['enabled'] = True

        put_resp = self.__do_put(runnertype_id, update_input)
        self.assertTrue(put_resp.json['enabled'])

    def __do_put(self, runner_type_id, runner_type):
        return self.app.put_json('/v1/runnertypes/%s' % runner_type_id, runner_type,
                                expect_errors=True)

    @staticmethod
    def __get_runnertype_id(resp_json):
        return resp_json['id']
