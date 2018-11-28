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
import warnings
import mock
import unittest2

from tests import base

from st2client import client
from st2client import models
from st2client.utils import httpclient


LOG = logging.getLogger(__name__)


RUNNER = {
    "enabled": True,
    "name": "marathon",
    "runner_parameters": {
        "var1": {"type": "string"}
    }
}

ACTION = {
    "ref": "mock.foobar",
    "runner_type": "marathon",
    "name": "foobar",
    "parameters": {},
    "enabled": True,
    "entry_point": "",
    "pack": "mocke"
}

EXECUTION = {
    "id": 12345,
    "action": {
        "ref": "mock.foobar"
    },
    "status": "failed",
    "result": "non-empty"
}


class TestExecutionResourceManager(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestExecutionResourceManager, cls).setUpClass()
        cls.client = client.Client()

    @mock.patch.object(
        models.ResourceManager, 'get_by_id',
        mock.MagicMock(return_value=models.Execution(**EXECUTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(return_value=models.Action(**ACTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(return_value=models.RunnerType(**RUNNER)))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(EXECUTION), 200, 'OK')))
    def test_rerun_with_no_params(self):
        self.client.executions.re_run(EXECUTION['id'], tasks=['foobar'])

        endpoint = '/executions/%s/re_run' % EXECUTION['id']

        data = {
            'tasks': ['foobar'],
            'reset': ['foobar'],
            'parameters': {},
            'delay': 0
        }

        httpclient.HTTPClient.post.assert_called_with(endpoint, data)

    @mock.patch.object(
        models.ResourceManager, 'get_by_id',
        mock.MagicMock(return_value=models.Execution(**EXECUTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(return_value=models.Action(**ACTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(return_value=models.RunnerType(**RUNNER)))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(EXECUTION), 200, 'OK')))
    def test_rerun_with_params(self):
        params = {
            'var1': 'testing...'
        }

        self.client.executions.re_run(
            EXECUTION['id'],
            tasks=['foobar'],
            parameters=params
        )

        endpoint = '/executions/%s/re_run' % EXECUTION['id']

        data = {
            'tasks': ['foobar'],
            'reset': ['foobar'],
            'parameters': params,
            'delay': 0
        }

        httpclient.HTTPClient.post.assert_called_with(endpoint, data)

    @mock.patch.object(
        models.ResourceManager, 'get_by_id',
        mock.MagicMock(return_value=models.Execution(**EXECUTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(return_value=models.Action(**ACTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(return_value=models.RunnerType(**RUNNER)))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(EXECUTION), 200, 'OK')))
    def test_rerun_with_delay(self):
        self.client.executions.re_run(EXECUTION['id'], tasks=['foobar'], delay=100)

        endpoint = '/executions/%s/re_run' % EXECUTION['id']

        data = {
            'tasks': ['foobar'],
            'reset': ['foobar'],
            'parameters': {},
            'delay': 100
        }

        httpclient.HTTPClient.post.assert_called_with(endpoint, data)

    @mock.patch.object(
        models.ResourceManager, 'get_by_id',
        mock.MagicMock(return_value=models.Execution(**EXECUTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(return_value=models.Action(**ACTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(return_value=models.RunnerType(**RUNNER)))
    @mock.patch.object(
        httpclient.HTTPClient, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(EXECUTION), 200, 'OK')))
    def test_pause(self):
        self.client.executions.pause(EXECUTION['id'])

        endpoint = '/executions/%s' % EXECUTION['id']

        data = {
            'status': 'pausing'
        }

        httpclient.HTTPClient.put.assert_called_with(endpoint, data)

    @mock.patch.object(
        models.ResourceManager, 'get_by_id',
        mock.MagicMock(return_value=models.Execution(**EXECUTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(return_value=models.Action(**ACTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(return_value=models.RunnerType(**RUNNER)))
    @mock.patch.object(
        httpclient.HTTPClient, 'put',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(EXECUTION), 200, 'OK')))
    def test_resume(self):
        self.client.executions.resume(EXECUTION['id'])

        endpoint = '/executions/%s' % EXECUTION['id']

        data = {
            'status': 'resuming'
        }

        httpclient.HTTPClient.put.assert_called_with(endpoint, data)

    @mock.patch.object(
        models.core.Resource, 'get_url_path_name',
        mock.MagicMock(return_value='executions'))
    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps([EXECUTION]), 200, 'OK')))
    def test_get_children(self):
        self.client.executions.get_children(EXECUTION['id'])

        endpoint = '/executions/%s/children' % EXECUTION['id']

        data = {
            'depth': -1
        }

        httpclient.HTTPClient.get.assert_called_with(url=endpoint, params=data)

    @mock.patch.object(
        models.ResourceManager, 'get_all',
        mock.MagicMock(return_value=[models.Execution(**EXECUTION)]))
    @mock.patch.object(warnings, 'warn')
    def test_st2client_liveactions_has_been_deprecated_and_emits_warning(self, mock_warn):
        self.assertEqual(mock_warn.call_args, None)

        self.client.liveactions.get_all()

        expected_msg = 'st2client.liveactions has been renamed'
        self.assertTrue(len(mock_warn.call_args_list) >= 1)
        self.assertTrue(expected_msg in mock_warn.call_args_list[0][0][0])
        self.assertEqual(mock_warn.call_args_list[0][0][1], DeprecationWarning)
