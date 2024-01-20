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
import mock

from tests import base

from st2client import shell
from st2client.models.core import ResourceManager
from st2client.models.action import Execution
from st2client.utils import httpclient

MOCK_MATCH_AND_EXECUTE_RESULT_1 = {
    "results": [
        {
            "execution": {
                "id": "mock-id",
            },
            "actionalias": {"ref": "mock-ref"},
        }
    ]
}

MOCK_MATCH_AND_EXECUTE_RESULT_2 = {
    "results": [
        {
            "execution": {"id": "mock-id-execute", "status": "succeeded"},
            "actionalias": {"ref": "mock-ref"},
            "liveaction": {
                "id": "mock-id",
            },
        }
    ]
}

MOCK_CREATE_EXECUTION_RESULT = {
    "id": "mock-id-format-execution",
    "status": "succeeded",
    "result": {"result": {"message": "Result formatted message"}},
}


class ActionAliasCommandTestCase(base.BaseCLITestCase):
    def __init__(self, *args, **kwargs):
        super(ActionAliasCommandTestCase, self).__init__(*args, **kwargs)
        self.shell = shell.Shell()

    @mock.patch.object(
        httpclient.HTTPClient,
        "post",
        mock.MagicMock(
            return_value=base.FakeResponse(
                json.dumps(MOCK_MATCH_AND_EXECUTE_RESULT_1), 200, "OK"
            )
        ),
    )
    def test_match_and_execute_success(self):
        ret = self.shell.run(["action-alias", "execute", "run whoami on localhost"])
        self.assertEqual(ret, 0)

        expected_args = {
            "command": "run whoami on localhost",
            "user": "",
            "source_channel": "cli",
        }
        httpclient.HTTPClient.post.assert_called_with(
            "/aliasexecution/match_and_execute", expected_args
        )

        mock_stdout = self.stdout.getvalue()

        self.assertTrue("Matching Action-alias: 'mock-ref'" in mock_stdout)
        self.assertTrue("st2 execution get mock-id" in mock_stdout)

    @mock.patch.object(
        httpclient.HTTPClient,
        "post",
        mock.MagicMock(
            side_effect=[
                base.FakeResponse(
                    json.dumps(MOCK_MATCH_AND_EXECUTE_RESULT_2), 200, "OK"
                ),
                base.FakeResponse(json.dumps(MOCK_CREATE_EXECUTION_RESULT), 200, "OK"),
            ]
        ),
    )
    @mock.patch.object(
        ResourceManager,
        "get_by_id",
        mock.MagicMock(return_value=Execution(**MOCK_CREATE_EXECUTION_RESULT)),
    )
    def test_test_command_success(self):
        ret = self.shell.run(["action-alias", "test", "run whoami on localhost"])
        self.assertEqual(ret, 0)

        expected_args = {
            "command": "run whoami on localhost",
            "user": "",
            "source_channel": "cli",
        }
        httpclient.HTTPClient.post.assert_any_call(
            "/aliasexecution/match_and_execute", expected_args
        )

        expected_args = {
            "action": "chatops.format_execution_result",
            "parameters": {"execution_id": "mock-id-execute"},
            "user": "",
        }
        httpclient.HTTPClient.post.assert_any_call("/executions", expected_args)

        mock_stdout = self.stdout.getvalue()

        self.assertTrue(
            "Execution (mock-id-execute) has been started, waiting for it to finish"
            in mock_stdout
        )
        self.assertTrue(
            "Execution (mock-id-format-execution) has been started, waiting for it to "
            "finish" in mock_stdout
        )
        self.assertTrue("Formatted ChatOps result message" in mock_stdout)
        self.assertTrue("Result formatted message" in mock_stdout)
