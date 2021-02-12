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
from st2client.utils import httpclient

MOCK_MATCH_AND_EXECUTE_RESULT = {
    "results": [
        {
            "execution": {
                "id": "mock-id",
            },
            "actionalias": {
                "ref": "mock-ref"
            }
        }
    ]
}


class ActionAliasCommandTestCase(base.BaseCLITestCase):
    def __init__(self, *args, **kwargs):
        super(ActionAliasCommandTestCase, self).__init__(*args, **kwargs)
        self.shell = shell.Shell()

    @mock.patch.object(
        httpclient.HTTPClient, 'post',
        mock.MagicMock(return_value=base.FakeResponse(json.dumps(MOCK_MATCH_AND_EXECUTE_RESULT),
                                                      200, 'OK')))
    def test_match_and_execute(self):
        ret = self.shell.run(['action-alias', 'execute', "run whoami on localhost"])
        self.assertEqual(ret, 0)

        expected_args = {
            'command': 'run whoami on localhost',
            'user': '',
            'source_channel': 'cli'
        }
        httpclient.HTTPClient.post.assert_called_with('/aliasexecution/match_and_execute',
                                                      expected_args)

        mock_stdout = self.stdout.getvalue()

        self.assertTrue("Matching Action-alias: 'mock-ref'" in mock_stdout)
        self.assertTrue("st2 execution get mock-id" in mock_stdout)
