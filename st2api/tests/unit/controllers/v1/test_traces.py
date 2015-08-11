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
    'traces': ['trace_empty.yaml', 'trace_one_each.yaml']
}


class TestTraces(FunctionalTest):

    models = None
    trace1 = None
    trace2 = None

    @classmethod
    def setUpClass(cls):
        super(TestTraces, cls).setUpClass()
        cls.models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                          fixtures_dict=TEST_MODELS)
        cls.trace1 = cls.models['traces']['trace_empty.yaml']
        cls.trace2 = cls.models['traces']['trace_one_each.yaml']

    def test_get_all(self):
        resp = self.app.get('/v1/traces')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2, '/v1/traces did not return all traces.')

        retrieved_trace_ids = [trace['trace_id'] for trace in resp.json]

        self.assertEqual(retrieved_trace_ids, [self.trace1.trace_id, self.trace2.trace_id],
                         'Incorrect traces retrieved.')
