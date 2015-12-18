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

import os
import signal
import datetime

import eventlet
from eventlet.green import subprocess

from st2common.constants import action as action_constants
from st2common.util import date as date_utils
from st2common.models.db.execution import ActionExecutionDB
from st2common.persistence.execution import ActionExecution
from st2tests.base import IntegrationTestCase
from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import FixturesLoader

__all__ = [
    'GarbageCollectorServiceTestCase'
]

TEST_FIXTURES = {
    'executions': [
        'execution1.yaml'
    ],
    'liveactions': [
        'liveaction4.yaml'
    ]
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ST2_CONFIG_PATH = os.path.join(BASE_DIR, '../../../conf/st2.tests.conf')
ST2_CONFIG_PATH = os.path.abspath(ST2_CONFIG_PATH)
BINARY = os.path.join(BASE_DIR, '../../../st2reactor/bin/st2garbagecollector')
BINARY = os.path.abspath(BINARY)
CMD = [BINARY, '--config-file', ST2_CONFIG_PATH]


class GarbageCollectorServiceTestCase(IntegrationTestCase, CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(GarbageCollectorServiceTestCase, cls).setUpClass()

    def setUp(self):
        super(GarbageCollectorServiceTestCase, self).setUp()
        fixtures_loader = FixturesLoader()
        self.models = fixtures_loader.load_models(fixtures_pack='generic',
                                                  fixtures_dict=TEST_FIXTURES)

    def test_garbage_collection(self):
        now = date_utils.get_datetime_utc_now()
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED

        # Insert come mock ActionExecutionDB objects with start_timestamp < TTL defined in the
        # config
        old_executions_count = 15
        ttl_days = 30
        timestamp = (now - datetime.timedelta(days=ttl_days))
        for index in range(0, old_executions_count):
            action_execution_db = ActionExecutionDB(start_timestamp=timestamp,
                                                    end_timestamp=timestamp,
                                                    status=status,
                                                    action={'ref': 'core.local'},
                                                    runner={'name': 'run-local'},
                                                    liveaction={'ref': 'foo'})
            ActionExecution.add_or_update(action_execution_db)

        # Insert come mock ActionExecutionDB objects with start_timestamp > TTL defined in the
        # config
        new_executions_count = 5
        ttl_days = 2
        timestamp = (now - datetime.timedelta(days=ttl_days))
        for index in range(0, new_executions_count):
            action_execution_db = ActionExecutionDB(start_timestamp=timestamp,
                                                    end_timestamp=timestamp,
                                                    status=status,
                                                    action={'ref': 'core.local'},
                                                    runner={'name': 'run-local'},
                                                    liveaction={'ref': 'foo'})
            ActionExecution.add_or_update(action_execution_db)

        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), (old_executions_count + new_executions_count))

        # Start garbage collector
        process = self._start_garbage_collector()

        # Give it some time to perform garbage collection and kill it
        eventlet.sleep(5)
        process.send_signal(signal.SIGKILL)
        self.remove_process(process=process)

        # Old execution should have been garbage collected
        execs = ActionExecution.get_all()
        self.assertEqual(len(execs), (new_executions_count))

    def _start_garbage_collector(self):
        process = subprocess.Popen(CMD, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=False, preexec_fn=os.setsid)
        self.add_process(process=process)
        return process
