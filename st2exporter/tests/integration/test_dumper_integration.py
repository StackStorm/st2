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
import Queue

import mock
import six

from st2common.models.api.execution import ActionExecutionAPI
from st2common.persistence.marker import DumperMarker
from st2common.util import isotime
from st2exporter.exporter.dumper import Dumper
from st2tests.base import DbTestCase
from st2tests.fixturesloader import FixturesLoader

DESCENDANTS_PACK = 'descendants'

DESCENDANTS_FIXTURES = {
    'executions': ['root_execution.yaml', 'child1_level1.yaml', 'child2_level1.yaml',
                   'child1_level2.yaml', 'child2_level2.yaml', 'child3_level2.yaml',
                   'child1_level3.yaml', 'child2_level3.yaml', 'child3_level3.yaml']
}


class TestDumper(DbTestCase):

    fixtures_loader = FixturesLoader()
    loaded_fixtures = fixtures_loader.load_fixtures(fixtures_pack=DESCENDANTS_PACK,
                                                    fixtures_dict=DESCENDANTS_FIXTURES)
    loaded_executions = loaded_fixtures['executions']
    execution_apis = []
    for execution in loaded_executions.values():
        execution_apis.append(ActionExecutionAPI(**execution))

    def get_queue(self):
        executions_queue = Queue.Queue()

        for execution in self.execution_apis:
            executions_queue.put(execution)
        return executions_queue

    @mock.patch.object(os.path, 'exists', mock.MagicMock(return_value=True))
    def test_write_marker_to_db(self):
        executions_queue = self.get_queue()
        dumper = Dumper(queue=executions_queue,
                        export_dir='/tmp', batch_size=5,
                        max_files_per_sleep=1,
                        file_prefix='st2-stuff-', file_format='json')
        timestamps = [isotime.parse(execution.end_timestamp) for execution in self.execution_apis]
        max_timestamp = max(timestamps)
        marker_db = dumper._write_marker_to_db(max_timestamp)
        persisted_marker = marker_db.marker
        self.assertTrue(isinstance(persisted_marker, six.string_types))
        self.assertEqual(isotime.parse(persisted_marker), max_timestamp)

    @mock.patch.object(os.path, 'exists', mock.MagicMock(return_value=True))
    def test_write_marker_to_db_marker_exists(self):
        executions_queue = self.get_queue()
        dumper = Dumper(queue=executions_queue,
                        export_dir='/tmp', batch_size=5,
                        max_files_per_sleep=1,
                        file_prefix='st2-stuff-', file_format='json')
        timestamps = [isotime.parse(execution.end_timestamp) for execution in self.execution_apis]
        max_timestamp = max(timestamps)
        first_marker_db = dumper._write_marker_to_db(max_timestamp)
        second_marker_db = dumper._write_marker_to_db(max_timestamp + datetime.timedelta(hours=1))
        markers = DumperMarker.get_all()
        self.assertEqual(len(markers), 1)
        final_marker_id = markers[0].id
        self.assertEqual(first_marker_db.id, final_marker_id)
        self.assertEqual(second_marker_db.id, final_marker_id)
        self.assertEqual(markers[0].marker, second_marker_db.marker)
        self.assertTrue(second_marker_db.updated_at > first_marker_db.updated_at)
