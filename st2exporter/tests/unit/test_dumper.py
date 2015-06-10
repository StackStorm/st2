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

import os
import Queue

import mock
import unittest2

from st2exporter.exporter.dumper import Dumper
from st2tests.fixturesloader import FixturesLoader

DESCENDANTS_PACK = 'descendants'

DESCENDANTS_FIXTURES = {
    'executions': ['root_execution.yaml', 'child1_level1.yaml', 'child2_level1.yaml',
                   'child1_level2.yaml', 'child2_level2.yaml', 'child3_level2.yaml',
                   'child1_level3.yaml', 'child2_level3.yaml', 'child3_level3.yaml']
}


class TestDumper(unittest2.TestCase):

    fixtures_loader = FixturesLoader()
    loaded_fixtures = fixtures_loader.load_fixtures(fixtures_pack=DESCENDANTS_PACK,
                                                    fixtures_dict=DESCENDANTS_FIXTURES)
    loaded_executions = loaded_fixtures['executions']

    def get_queue(self):
        executions_queue = Queue.Queue()

        for execution in self.loaded_executions:
            executions_queue.put(execution)
        return executions_queue

    @mock.patch.object(os.path, 'exists', mock.MagicMock(return_value=True))
    def test_get_batch_batch_size_greater_than_actual(self):
        executions_queue = self.get_queue()
        qsize = executions_queue.qsize()
        self.assertTrue(qsize > 0)
        dumper = Dumper(queue=executions_queue, batch_size=2*qsize,
                        export_dir='/tmp')
        batch = dumper._get_batch()
        self.assertEqual(len(batch), qsize)

    @mock.patch.object(os.path, 'exists', mock.MagicMock(return_value=True))
    def test_get_batch_batch_size_lesser_than_actual(self):
        executions_queue = self.get_queue()
        qsize = executions_queue.qsize()
        self.assertTrue(qsize > 0)
        expected_batch_size = int(qsize/2)
        dumper = Dumper(queue=executions_queue,
                        batch_size=expected_batch_size,
                        export_dir='/tmp')
        batch = dumper._get_batch()
        self.assertEqual(len(batch), expected_batch_size)

    def test_get_file_name(self):
        dumper = Dumper(queue=self.get_queue(),
                        export_dir='/tmp',
                        file_prefix='st2-stuff-', file_format='json')
        file_name = dumper._get_file_name()
        self.assertTrue(file_name.startswith('/tmp/st2-stuff-'))
        self.assertTrue(file_name.endswith('json'))
