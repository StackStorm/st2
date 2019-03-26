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

from st2api.controllers.v1.traces import TracesController
from st2tests.fixturesloader import FixturesLoader

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

FIXTURES_PACK = 'traces'

TEST_MODELS = {
    'traces': [
        'trace_empty.yaml',
        'trace_one_each.yaml',
        'trace_multiple_components.yaml'
    ]
}


class TracesControllerTestCase(FunctionalTest,
                               APIControllerWithIncludeAndExcludeFilterTestCase):
    get_all_path = '/v1/traces'
    controller_cls = TracesController
    include_attribute_field_name = 'trace_tag'
    exclude_attribute_field_name = 'start_timestamp'

    models = None
    trace1 = None
    trace2 = None
    trace3 = None

    @classmethod
    def setUpClass(cls):
        super(TracesControllerTestCase, cls).setUpClass()
        cls.models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                          fixtures_dict=TEST_MODELS)
        cls.trace1 = cls.models['traces']['trace_empty.yaml']
        cls.trace2 = cls.models['traces']['trace_one_each.yaml']
        cls.trace3 = cls.models['traces']['trace_multiple_components.yaml']

    def test_get_all_and_minus_one(self):
        resp = self.app.get('/v1/traces')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 3, '/v1/traces did not return all traces.')

        # Note: traces are returned sorted by start_timestamp in descending order by default
        retrieved_trace_tags = [trace['trace_tag'] for trace in resp.json]
        self.assertEqual(retrieved_trace_tags,
                         [self.trace3.trace_tag, self.trace2.trace_tag, self.trace1.trace_tag],
                         'Incorrect traces retrieved.')

        resp = self.app.get('/v1/traces/?limit=-1')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 3, '/v1/traces did not return all traces.')

        # Note: traces are returned sorted by start_timestamp in descending order by default
        retrieved_trace_tags = [trace['trace_tag'] for trace in resp.json]
        self.assertEqual(retrieved_trace_tags,
                         [self.trace3.trace_tag, self.trace2.trace_tag, self.trace1.trace_tag],
                         'Incorrect traces retrieved.')

    def test_get_all_ascending_and_descending(self):
        resp = self.app.get('/v1/traces?sort_asc=True')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 3, '/v1/traces did not return all traces.')

        retrieved_trace_tags = [trace['trace_tag'] for trace in resp.json]
        self.assertEqual(retrieved_trace_tags,
                         [self.trace1.trace_tag, self.trace2.trace_tag, self.trace3.trace_tag],
                         'Incorrect traces retrieved.')

        resp = self.app.get('/v1/traces?sort_desc=True')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 3, '/v1/traces did not return all traces.')

        retrieved_trace_tags = [trace['trace_tag'] for trace in resp.json]
        self.assertEqual(retrieved_trace_tags,
                         [self.trace3.trace_tag, self.trace2.trace_tag, self.trace1.trace_tag],
                         'Incorrect traces retrieved.')

    def test_get_all_limit(self):
        resp = self.app.get('/v1/traces?limit=1')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1, '/v1/traces did not return all traces.')

        retrieved_trace_tags = [trace['trace_tag'] for trace in resp.json]
        self.assertEqual(retrieved_trace_tags,
                         [self.trace3.trace_tag], 'Incorrect traces retrieved.')

    def test_get_all_limit_negative_number(self):
        resp = self.app.get('/v1/traces?limit=-22', expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(resp.json['faultstring'],
                         u'Limit, "-22" specified, must be a positive number.')

    def test_get_by_id(self):
        resp = self.app.get('/v1/traces/%s' % self.trace1.id)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['id'], str(self.trace1.id),
                         'Incorrect trace retrieved.')

    def test_query_by_trace_tag(self):
        resp = self.app.get('/v1/traces?trace_tag=test-trace-1')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1, '/v1/traces?trace_tag=x did not return correct trace.')

        self.assertEqual(resp.json[0]['trace_tag'], self.trace1['trace_tag'],
                         'Correct trace not returned.')

    def test_query_by_action_execution(self):
        execution_id = self.trace3['action_executions'][0].object_id
        resp = self.app.get('/v1/traces?execution=%s' % execution_id)

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1,
                         '/v1/traces?execution=x did not return correct trace.')
        self.assertEqual(resp.json[0]['trace_tag'], self.trace3['trace_tag'],
                         'Correct trace not returned.')

    def test_query_by_rule(self):
        rule_id = self.trace3['rules'][0].object_id
        resp = self.app.get('/v1/traces?rule=%s' % rule_id)

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1, '/v1/traces?rule=x did not return correct trace.')
        self.assertEqual(resp.json[0]['trace_tag'], self.trace3['trace_tag'],
                         'Correct trace not returned.')

    def test_query_by_trigger_instance(self):
        trigger_instance_id = self.trace3['trigger_instances'][0].object_id
        resp = self.app.get('/v1/traces?trigger_instance=%s' % trigger_instance_id)

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1,
                         '/v1/traces?trigger_instance=x did not return correct trace.')
        self.assertEqual(resp.json[0]['trace_tag'], self.trace3['trace_tag'],
                         'Correct trace not returned.')

    def _insert_mock_models(self):
        trace_ids = [trace['id'] for trace in self.models['traces'].values()]
        return trace_ids

    def _delete_mock_models(self, object_ids):
        pass
