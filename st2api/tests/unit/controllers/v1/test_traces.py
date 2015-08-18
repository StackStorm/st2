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

from st2tests.fixturesloader import FixturesLoader
from tests import FunctionalTest

FIXTURES_PACK = 'traces'

TEST_MODELS = {
    'traces': [
        'trace_empty.yaml',
        'trace_one_each.yaml',
        'trace_multiple_components.yaml'
    ]
}


class TestTraces(FunctionalTest):

    models = None
    trace1 = None
    trace2 = None
    trace3 = None

    @classmethod
    def setUpClass(cls):
        super(TestTraces, cls).setUpClass()
        cls.models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                          fixtures_dict=TEST_MODELS)
        cls.trace1 = cls.models['traces']['trace_empty.yaml']
        cls.trace2 = cls.models['traces']['trace_one_each.yaml']
        cls.trace3 = cls.models['traces']['trace_multiple_components.yaml']

    def test_get_all(self):
        resp = self.app.get('/v1/traces')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 3, '/v1/traces did not return all traces.')

        retrieved_trace_tags = [trace['trace_tag'] for trace in resp.json]

        self.assertEqual(retrieved_trace_tags,
                         [self.trace1.trace_tag, self.trace2.trace_tag, self.trace3.trace_tag],
                         'Incorrect traces retrieved.')

    def test_query_by_trace_tag(self):
        resp = self.app.get('/v1/traces/?trace_tag=test-trace-1')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1, '/v1/traces?trace_tag=x did not return correct trace.')

        self.assertEqual(resp.json[0]['trace_tag'], self.trace1['trace_tag'],
                         'Correct trace not returned.')

    def test_query_by_action_execution(self):
        resp = self.app.get('/v1/traces/?execution=action_execution_2')

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1,
                         '/v1/traces?execution=x did not return correct trace.')
        self.assertEqual(resp.json[0]['trace_tag'], self.trace3['trace_tag'],
                         'Correct trace not returned.')

    def test_query_by_rule(self):
        resp = self.app.get('/v1/traces/?rule=rule_2')

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1, '/v1/traces?rule=x did not return correct trace.')
        self.assertEqual(resp.json[0]['trace_tag'], self.trace3['trace_tag'],
                         'Correct trace not returned.')

    def test_query_by_trigger_instance(self):
        resp = self.app.get('/v1/traces/?trigger_instance=trigger_instance_4')

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1,
                         '/v1/traces?trigger_instance=x did not return correct trace.')
        self.assertEqual(resp.json[0]['trace_tag'], self.trace3['trace_tag'],
                         'Correct trace not returned.')
