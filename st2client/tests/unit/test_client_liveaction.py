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

import json
import logging
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

LIVE_ACTION = {
    "id": 12345,
    "action": {
        "ref": "mock.foobar"
    },
    "status": "failed",
    "result": "non-empty"
}


class TestLiveActionResourceManager(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestLiveActionResourceManager, cls).setUpClass()
        cls.client = client.Client()

    @mock.patch.object(
        models.ResourceManager, 'get_by_id',
        mock.MagicMock(return_vaue=models.LiveAction(**LIVE_ACTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(return_value=models.Action(**ACTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(return_value=models.RunnerType(**RUNNER)))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_rerun_with_no_params(self):
        self.client.liveactions.re_run(LIVE_ACTION['id'], tasks=['foobar'])

        endpoint = '/executions/%s/re_run' % LIVE_ACTION['id']

        data = {
            'tasks': ['foobar'],
            'reset': ['foobar'],
            'parameters': {}
        }

        httpclient.HTTPClient.post.assert_called_with(endpoint, data)

    @mock.patch.object(
        models.ResourceManager, 'get_by_id',
        mock.MagicMock(return_vaue=models.LiveAction(**LIVE_ACTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_ref_or_id',
        mock.MagicMock(return_value=models.Action(**ACTION)))
    @mock.patch.object(
        models.ResourceManager, 'get_by_name',
        mock.MagicMock(return_value=models.RunnerType(**RUNNER)))
    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(LIVE_ACTION), 200, 'OK')))
    def test_rerun_with_params(self):
        params = {
            'var1': 'testing...'
        }

        self.client.liveactions.re_run(
            LIVE_ACTION['id'],
            tasks=['foobar'],
            parameters=params
        )

        endpoint = '/executions/%s/re_run' % LIVE_ACTION['id']

        data = {
            'tasks': ['foobar'],
            'reset': ['foobar'],
            'parameters': params
        }

        httpclient.HTTPClient.post.assert_called_with(endpoint, data)
