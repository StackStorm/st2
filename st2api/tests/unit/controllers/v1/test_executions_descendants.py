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

from st2tests.fixturesloader import FixturesLoader
from st2tests.api import FunctionalTest


DESCENDANTS_PACK = 'descendants'

DESCENDANTS_FIXTURES = {
    'executions': ['root_execution.yaml', 'child1_level1.yaml', 'child2_level1.yaml',
                   'child1_level2.yaml', 'child2_level2.yaml', 'child3_level2.yaml',
                   'child1_level3.yaml', 'child2_level3.yaml', 'child3_level3.yaml']
}


class ActionExecutionControllerTestCaseDescendantsTest(FunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(ActionExecutionControllerTestCaseDescendantsTest, cls).setUpClass()
        cls.MODELS = FixturesLoader().save_fixtures_to_db(fixtures_pack=DESCENDANTS_PACK,
                                                          fixtures_dict=DESCENDANTS_FIXTURES)

    def test_get_all_descendants(self):
        root_execution = self.MODELS['executions']['root_execution.yaml']
        resp = self.app.get('/v1/executions/%s/children' % str(root_execution.id))
        self.assertEqual(resp.status_int, 200)

        all_descendants_ids = [descendant['id'] for descendant in resp.json]
        all_descendants_ids.sort()

        # everything except the root_execution
        expected_ids = [str(v.id) for _, v in six.iteritems(self.MODELS['executions'])
                        if v.id != root_execution.id]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)

    def test_get_all_descendants_depth_neg_1(self):
        root_execution = self.MODELS['executions']['root_execution.yaml']
        resp = self.app.get('/v1/executions/%s/children?depth=-1' % str(root_execution.id))
        self.assertEqual(resp.status_int, 200)

        all_descendants_ids = [descendant['id'] for descendant in resp.json]
        all_descendants_ids.sort()

        # everything except the root_execution
        expected_ids = [str(v.id) for _, v in six.iteritems(self.MODELS['executions'])
                        if v.id != root_execution.id]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)

    def test_get_1_level_descendants(self):
        root_execution = self.MODELS['executions']['root_execution.yaml']
        resp = self.app.get('/v1/executions/%s/children?depth=1' % str(root_execution.id))
        self.assertEqual(resp.status_int, 200)

        all_descendants_ids = [descendant['id'] for descendant in resp.json]
        all_descendants_ids.sort()

        # All children of root_execution
        expected_ids = [str(v.id) for _, v in six.iteritems(self.MODELS['executions'])
                        if v.parent == str(root_execution.id)]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)
