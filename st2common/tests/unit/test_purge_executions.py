# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the 'License'); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import FixturesLoader
from st2common.persistence.execution import ActionExecution
from tools.purge_executions import purge_executions

TEST_FIXTURES = {
    'executions': [
        'execution1.yaml'
    ],
    'liveactions': [
        'liveaction4.yaml'
    ]
}


class TestPurgeExecutions(CleanDbTestCase):

    @classmethod
    def setUpClass(cls):
        CleanDbTestCase.setUpClass()
        super(TestPurgeExecutions, cls).setUpClass()

    def setUp(self):
        super(TestPurgeExecutions, self).setUp()
        fixtures_loader = FixturesLoader()
        fixtures_loader.save_fixtures_to_db(fixtures_pack='generic',
                                            fixtures_dict=TEST_FIXTURES)

    def test_purge_executions_no_timestamp(self):
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)
        purge_executions(timestamp=None)
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)

    def test_purge_executions_action_not_present(self):
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)
        purge_executions(action_ref='core.localzzz')
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)

    def test_purge_executions_default_timestamp(self):
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)
        purge_executions()
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), 1)
