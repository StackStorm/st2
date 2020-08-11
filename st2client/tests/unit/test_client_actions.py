# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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
import unittest2

from tests import base

from st2client import client
from st2client.utils import httpclient


LOG = logging.getLogger(__name__)


EXECUTION = {
    "id": 12345,
    "action": {
        "ref": "mock.foobar"
    },
    "status": "failed",
    "result": "non-empty"
}

ENTRYPOINT = (
    "version: 1.0"

    "description: A basic workflow that runs an arbitrary linux command."

    "input:"
    "  - cmd"
    "  - timeout"

    "tasks:"
    "  task1:"
    "    action: core.local cmd=<% ctx(cmd) %> timeout=<% ctx(timeout) %>"
    "    next:"
    "      - when: <% succeeded() %>"
    "        publish:"
    "          - stdout: <% result().stdout %>"
    "          - stderr: <% result().stderr %>"

    "output:"
    "  - stdout: <% ctx(stdout) %>"
)


class TestActionResourceManager(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestActionResourceManager, cls).setUpClass()
        cls.client = client.Client()

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(ENTRYPOINT), 200, 'OK')))
    def test_get_action_entry_point_by_ref(self):
        actual_entrypoint = self.client.actions.get_entrypoint(EXECUTION['action']['ref'])
        actual_entrypoint = json.loads(actual_entrypoint)

        endpoint = '/actions/views/entry_point/%s' % EXECUTION['action']['ref']
        httpclient.HTTPClient.get.assert_called_with(endpoint)

        self.assertEqual(ENTRYPOINT, actual_entrypoint)

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(ENTRYPOINT), 200, 'OK')))
    def test_get_action_entry_point_by_id(self):
        actual_entrypoint = self.client.actions.get_entrypoint(EXECUTION['id'])
        actual_entrypoint = json.loads(actual_entrypoint)

        endpoint = '/actions/views/entry_point/%s' % EXECUTION['id']
        httpclient.HTTPClient.get.assert_called_with(endpoint)

        self.assertEqual(ENTRYPOINT, actual_entrypoint)

    @mock.patch.object(
        httpclient.HTTPClient, 'get',
        mock.MagicMock(return_value=base.FakeResponse(
            json.dumps({}), 404, '404 Client Error: Not Found'
        )))
    def test_get_non_existent_action_entry_point(self):
        with self.assertRaisesRegexp(Exception, '404 Client Error: Not Found'):
            self.client.actions.get_entrypoint('nonexistentpack.nonexistentaction')

        endpoint = '/actions/views/entry_point/%s' % 'nonexistentpack.nonexistentaction'
        httpclient.HTTPClient.get.assert_called_with(endpoint)
