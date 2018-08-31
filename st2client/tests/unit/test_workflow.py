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

from __future__ import absolute_import

import json
import logging
import mock
import os
import tempfile

from st2client.commands import workflow
from st2client import shell
from st2client import models
from st2client.utils import httpclient
from tests import base as st2cli_tests


LOG = logging.getLogger(__name__)

MOCK_ACTION = {
    'ref': 'mock.foobar',
    'runner_type': 'mock-runner',
    'pack': 'mock',
    'name': 'foobar',
    'parameters': {},
    'enabled': True,
    'entry_point': 'workflows/foobar.yaml'
}

MOCK_WF_DEF = """
version: 1.0
description: A basic sequential workflow.
tasks:
  task1:
    action: core.echo message="Hello, World!"
"""

MOCK_RESULT = []


def get_by_ref(**kwargs):
    return models.Action(**MOCK_ACTION)


class WorkflowCommandTestCase(st2cli_tests.BaseCLITestCase):

    def __init__(self, *args, **kwargs):
        super(WorkflowCommandTestCase, self).__init__(*args, **kwargs)
        self.shell = shell.Shell()

    @mock.patch.object(
        httpclient.HTTPClient, 'post_raw',
        mock.MagicMock(return_value=st2cli_tests.FakeResponse(json.dumps(MOCK_RESULT), 200, 'OK')))
    def test_inspect_file(self):
        fd, path = tempfile.mkstemp(suffix='.yaml')

        try:
            with open(path, 'a') as f:
                f.write(MOCK_WF_DEF)

            retcode = self.shell.run(['workflow', 'inspect', '--file', path])

            self.assertEqual(retcode, 0)

            httpclient.HTTPClient.post_raw.assert_called_with(
                '/inspect',
                MOCK_WF_DEF,
                headers={'content-type': 'text/plain'}
            )
        finally:
            os.close(fd)
            os.unlink(path)

    @mock.patch.object(
        httpclient.HTTPClient, 'post_raw',
        mock.MagicMock(return_value=st2cli_tests.FakeResponse(json.dumps(MOCK_RESULT), 200, 'OK')))
    def test_inspect_bad_file(self):
        retcode = self.shell.run(['workflow', 'inspect', '--file', '/tmp/foobar'])

        self.assertEqual(retcode, 1)
        self.assertIn('does not exist', self.stdout.getvalue())
        self.assertFalse(httpclient.HTTPClient.post_raw.called)

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(side_effect=get_by_ref))
    @mock.patch.object(
        workflow.WorkflowInspectionCommand, 'get_file_content',
        mock.MagicMock(return_value=MOCK_WF_DEF))
    @mock.patch.object(
        httpclient.HTTPClient, 'post_raw',
        mock.MagicMock(return_value=st2cli_tests.FakeResponse(json.dumps(MOCK_RESULT), 200, 'OK')))
    def test_inspect_action(self):
        retcode = self.shell.run(['workflow', 'inspect', '--action', 'mock.foobar'])

        self.assertEqual(retcode, 0)

        httpclient.HTTPClient.post_raw.assert_called_with(
            '/inspect',
            MOCK_WF_DEF,
            headers={'content-type': 'text/plain'}
        )

    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(return_value=None))
    @mock.patch.object(
        httpclient.HTTPClient, 'post_raw',
        mock.MagicMock(return_value=st2cli_tests.FakeResponse(json.dumps(MOCK_RESULT), 200, 'OK')))
    def test_inspect_bad_action(self):
        retcode = self.shell.run(['workflow', 'inspect', '--action', 'mock.foobar'])

        self.assertEqual(retcode, 1)
        self.assertIn('Unable to identify action', self.stdout.getvalue())
        self.assertFalse(httpclient.HTTPClient.post_raw.called)
