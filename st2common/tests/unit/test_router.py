# Copyright 2026 The StackStorm Authors.
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

import unittest

import mock

from st2common.router import Router


class RouterMatchTestCase(unittest.TestCase):
    def _get_router(self):
        router = Router(auth=False)
        router.spec = {
            "paths": {
                "/api/v1/keys/{name}": {
                    "get": {"operationId": "st2api.controllers.v1.keyvalue:get_one"}
                }
            }
        }
        mapper = router.routes.submapper(
            _api_path="/api/v1/keys/{name}",
            _api_method="get",
            conditions={"method": ["GET"]},
        )
        mapper.connect(None, "/v1/keys/{name}")
        return router

    def _match(self, path):
        request = mock.Mock()
        request.path = path
        request.environ = {"REQUEST_METHOD": "GET"}
        return self._get_router().match(request)

    def test_match_plain_name(self):
        endpoint, path_vars = self._match("/v1/keys/key1")
        self.assertEqual(path_vars, {"name": "key1"})

    def test_match_name_with_escaped_slash(self):
        # A key value pair name may contain "/". The client URL encodes it as
        # "%2F" and the router must hand the decoded name to the controller
        # instead of failing to match the route.
        endpoint, path_vars = self._match("/v1/keys/foo%2Fbar")
        self.assertEqual(path_vars, {"name": "foo/bar"})

    def test_match_name_with_escaped_space(self):
        endpoint, path_vars = self._match("/v1/keys/foo%20bar")
        self.assertEqual(path_vars, {"name": "foo bar"})


if __name__ == "__main__":
    unittest.main()
