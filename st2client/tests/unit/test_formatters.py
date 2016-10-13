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
import os
import sys
import mock
import json
import logging
import tempfile
import unittest2

from tests import base
from tests.fixtures import loader

from st2client import shell
from st2client.utils import jsutil
from st2client.utils import httpclient
from st2client.utils import color


LOG = logging.getLogger(__name__)

FIXTURES_MANIFEST = {
    'executions': ['execution.json',
                   'execution_result_has_carriage_return.json'],
    'results': ['execution_get_default.txt',
                'execution_get_detail.txt',
                'execution_get_result_by_key.txt',
                'execution_result_has_carriage_return.txt',
                'execution_get_attributes.txt',
                'execution_list_attr_start_timestamp.txt',
                'execution_list_empty_response_start_timestamp_attr.txt']
}

FIXTURES = loader.load_fixtures(fixtures_dict=FIXTURES_MANIFEST)
EXECUTION = FIXTURES['executions']['execution.json']
HAS_CARRIAGE_RETURN = FIXTURES['executions']['execution_result_has_carriage_return.json']


class TestExecutionResultFormatter(unittest2.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestExecutionResultFormatter, self).__init__(*args, **kwargs)
        self.shell = shell.Shell()
        color.DISABLED = True

    def setUp(self):
        self.fd, self.path = tempfile.mkstemp()
        self._redirect_console(self.path)

    def tearDown(self):
        self._undo_console_redirect()
        os.close(self.fd)
        os.unlink(self.path)

    def _redirect_console(self, path):
        sys.stdout = open(path, 'w')
        sys.stderr = open(path, 'w')

    def _undo_console_redirect(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

    def test_console_redirect(self):
        message = 'Hello, World!'
        print(message)
        self._undo_console_redirect()
        with open(self.path, 'r') as fd:
            content = fd.read().replace('\n', '')
        self.assertEqual(content, message)

    def test_execution_get_default(self):
        argv = ['execution', 'get', EXECUTION['id']]
        content = self._get_execution(argv)
        self.assertEqual(content, FIXTURES['results']['execution_get_default.txt'])

    def test_execution_get_attributes(self):
        argv = ['execution', 'get', EXECUTION['id'], '--attr', 'status', 'end_timestamp']
        content = self._get_execution(argv)
        self.assertEqual(content, FIXTURES['results']['execution_get_attributes.txt'])

    def test_execution_get_default_in_json(self):
        argv = ['execution', 'get', EXECUTION['id'], '-j']
        content = self._get_execution(argv)
        self.assertEqual(json.loads(content),
                         jsutil.get_kvps(EXECUTION, ['id', 'status', 'parameters', 'result']))

    def test_execution_get_detail(self):
        argv = ['execution', 'get', EXECUTION['id'], '-d']
        content = self._get_execution(argv)
        self.assertEqual(content, FIXTURES['results']['execution_get_detail.txt'])

    def test_execution_get_detail_in_json(self):
        argv = ['execution', 'get', EXECUTION['id'], '-d', '-j']
        content = self._get_execution(argv)
        content_dict = json.loads(content)
        # Sufficient to check if output contains all expected keys. The entire result will not
        # match as content will contain characters which improve rendering.
        for k in six.iterkeys(EXECUTION):
            if k in content:
                continue
            self.assertTrue(False, 'Missing key %s. %s != %s' % (k, EXECUTION, content_dict))

    def test_execution_get_result_by_key(self):
        argv = ['execution', 'get', EXECUTION['id'], '-k', 'localhost.stdout']
        content = self._get_execution(argv)
        self.assertEqual(content, FIXTURES['results']['execution_get_result_by_key.txt'])

    def test_execution_get_result_by_key_in_json(self):
        argv = ['execution', 'get', EXECUTION['id'], '-k', 'localhost.stdout', '-j']
        content = self._get_execution(argv)
        self.assertDictEqual(json.loads(content),
                             jsutil.get_kvps(EXECUTION, ['result.localhost.stdout']))

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(HAS_CARRIAGE_RETURN), 200, 'OK')))
    def test_execution_get_detail_with_carriage_return(self):
        argv = ['execution', 'get', HAS_CARRIAGE_RETURN['id'], '-d']
        self.assertEqual(self.shell.run(argv), 0)
        self._undo_console_redirect()
        with open(self.path, 'r') as fd:
            content = fd.read()
        self.assertEqual(
            content, FIXTURES['results']['execution_result_has_carriage_return.txt'])

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps([EXECUTION]), 200, 'OK')))
    def test_execution_list_attribute_provided(self):
        # Client shouldn't throw if "-a" flag is provided when listing executions
        argv = ['execution', 'list', '-a', 'start_timestamp']
        self.assertEqual(self.shell.run(argv), 0)
        self._undo_console_redirect()

        with open(self.path, 'r') as fd:
            content = fd.read()
        self.assertEqual(
            content, FIXTURES['results']['execution_list_attr_start_timestamp.txt'])

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps([]), 200, 'OK')))
    def test_execution_list_attribute_provided_empty_response(self):
        # Client shouldn't throw if "-a" flag is provided, but there are no executions
        argv = ['execution', 'list', '-a', 'start_timestamp']
        self.assertEqual(self.shell.run(argv), 0)
        self._undo_console_redirect()

        with open(self.path, 'r') as fd:
            content = fd.read()
        self.assertEqual(
            content, FIXTURES['results']['execution_list_empty_response_start_timestamp_attr.txt'])

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(EXECUTION), 200, 'OK')))
    def _get_execution(self, argv):
        self.assertEqual(self.shell.run(argv), 0)
        self._undo_console_redirect()
        with open(self.path, 'r') as fd:
            content = fd.read()

        return content
