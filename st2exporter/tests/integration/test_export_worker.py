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

import datetime
import os

import mock

from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.db.marker import DumperMarkerDB
from st2common.persistence.marker import DumperMarker
from st2common.util import isotime
from st2common.util import date as date_utils
from st2exporter.worker import ExecutionsExporter
from st2tests.base import DbTestCase
from st2tests.fixturesloader import FixturesLoader
import st2tests.config as tests_config
tests_config.parse_args()

DESCENDANTS_PACK = 'descendants'

DESCENDANTS_FIXTURES = {
    'executions': ['root_execution.yaml', 'child1_level1.yaml', 'child2_level1.yaml',
                   'child1_level2.yaml', 'child2_level2.yaml', 'child3_level2.yaml',
                   'child1_level3.yaml', 'child2_level3.yaml', 'child3_level3.yaml']
}


class TestExportWorker(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestExportWorker, cls).setUpClass()
        fixtures_loader = FixturesLoader()
        loaded_fixtures = fixtures_loader.save_fixtures_to_db(fixtures_pack=DESCENDANTS_PACK,
                                                              fixtures_dict=DESCENDANTS_FIXTURES)
        TestExportWorker.saved_executions = loaded_fixtures['executions']

    @mock.patch.object(os.path, 'exists', mock.MagicMock(return_value=True))
    def test_get_marker_from_db(self):
        marker_dt = date_utils.get_datetime_utc_now() - datetime.timedelta(minutes=5)
        marker_db = DumperMarkerDB(marker=isotime.format(marker_dt, offset=False),
                                   updated_at=date_utils.get_datetime_utc_now())
        DumperMarker.add_or_update(marker_db)
        exec_exporter = ExecutionsExporter(None, None)
        export_marker = exec_exporter._get_export_marker_from_db()
        self.assertEqual(export_marker, date_utils.add_utc_tz(marker_dt))

    @mock.patch.object(os.path, 'exists', mock.MagicMock(return_value=True))
    def test_get_missed_executions_from_db_no_marker(self):
        exec_exporter = ExecutionsExporter(None, None)
        all_execs = exec_exporter._get_missed_executions_from_db(export_marker=None)
        self.assertEqual(len(all_execs), len(self.saved_executions.values()))

    @mock.patch.object(os.path, 'exists', mock.MagicMock(return_value=True))
    def test_get_missed_executions_from_db_with_marker(self):
        exec_exporter = ExecutionsExporter(None, None)
        all_execs = exec_exporter._get_missed_executions_from_db(export_marker=None)
        min_timestamp = min([item.end_timestamp for item in all_execs])
        marker = min_timestamp + datetime.timedelta(seconds=1)
        execs_greater_than_marker = [item for item in all_execs if item.end_timestamp > marker]
        all_execs = exec_exporter._get_missed_executions_from_db(export_marker=marker)
        self.assertTrue(len(all_execs) > 0)
        self.assertTrue(len(all_execs) == len(execs_greater_than_marker))
        for item in all_execs:
            self.assertTrue(item.end_timestamp > marker)

    @mock.patch.object(os.path, 'exists', mock.MagicMock(return_value=True))
    def test_bootstrap(self):
        exec_exporter = ExecutionsExporter(None, None)
        exec_exporter._bootstrap()
        self.assertEqual(exec_exporter.pending_executions.qsize(), len(self.saved_executions))

        count = 0
        while count < exec_exporter.pending_executions.qsize():
            self.assertTrue(isinstance(exec_exporter.pending_executions.get(), ActionExecutionAPI))
            count += 1

    @mock.patch.object(os.path, 'exists', mock.MagicMock(return_value=True))
    def test_process(self):
        some_execution = self.saved_executions.values()[5]
        exec_exporter = ExecutionsExporter(None, None)
        self.assertEqual(exec_exporter.pending_executions.qsize(), 0)
        exec_exporter.process(some_execution)
        self.assertEqual(exec_exporter.pending_executions.qsize(), 1)
        some_execution.status = 'scheduled'
        exec_exporter.process(some_execution)
        self.assertEqual(exec_exporter.pending_executions.qsize(), 1)

    @classmethod
    def tearDownClass(cls):
        super(TestExportWorker, cls).tearDownClass()
