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

from st2common.exceptions.trace import TraceNotFoundException
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.trace import Trace
import st2common.services.action as action_services
from st2tests.fixturesloader import FixturesLoader
from st2tests import DbTestCase

FIXTURES_PACK = 'traces'

TEST_MODELS = {
    'executions': ['traceable_execution.yaml'],
    'liveactions': ['traceable_liveaction.yaml'],
    'actions': ['chain1.yaml'],
    'runners': ['actionchain.yaml']
}


class TraceInjectionTests(DbTestCase):

    models = None
    traceable_liveaction = None
    traceable_execution = None
    action = None

    @classmethod
    def setUpClass(cls):
        super(TraceInjectionTests, cls).setUpClass()
        cls.models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                          fixtures_dict=TEST_MODELS)

        cls.traceable_liveaction = cls.models['liveactions']['traceable_liveaction.yaml']
        cls.traceable_execution = cls.models['executions']['traceable_execution.yaml']
        cls.action = cls.models['actions']['chain1.yaml']

    def test_trace_provided(self):
        self.traceable_liveaction['context']['trace_context'] = {'trace_tag': 'OohLaLaLa'}
        action_services.request(self.traceable_liveaction)
        traces = Trace.get_all()
        self.assertEqual(len(traces), 1)
        self.assertEqual(len(traces[0]['action_executions']), 1)

        # Let's use existing trace id in trace context.
        # We shouldn't create new trace object.
        trace_id = str(traces[0].id)
        self.traceable_liveaction['context']['trace_context'] = {'id_': trace_id}
        action_services.request(self.traceable_liveaction)
        traces = Trace.get_all()
        self.assertEqual(len(traces), 1)
        self.assertEqual(len(traces[0]['action_executions']), 2)

    def test_trace_tag_resuse(self):
        self.traceable_liveaction['context']['trace_context'] = {'trace_tag': 'blank space'}
        action_services.request(self.traceable_liveaction)
        # Let's use same trace tag again and we should see two trace objects in db.
        action_services.request(self.traceable_liveaction)
        traces = Trace.query(**{'trace_tag': 'blank space'})
        self.assertEqual(len(traces), 2)

    def test_invalid_trace_id_provided(self):
        liveactions = LiveAction.get_all()
        self.assertEqual(len(liveactions), 1)  # fixtures loads it.
        self.traceable_liveaction['context']['trace_context'] = {'id_': 'balleilaka'}

        self.assertRaises(TraceNotFoundException, action_services.request,
                          self.traceable_liveaction)

        # Make sure no liveactions are left behind
        liveactions = LiveAction.get_all()
        self.assertEqual(len(liveactions), 0)
