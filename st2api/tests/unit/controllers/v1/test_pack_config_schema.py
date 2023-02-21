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

import glob

from st2tests.api import FunctionalTest

# import this so that pants can infer dependencies for the glob below
from st2tests.fixtures.packs.all_packs_glob import PACKS_PATH

__all__ = ["PackConfigSchemasControllerTestCase"]

CONFIG_SCHEMA_COUNT = len(glob.glob(f"{PACKS_PATH}/*/config.schema.yaml"))
assert CONFIG_SCHEMA_COUNT > 1


class PackConfigSchemasControllerTestCase(FunctionalTest):
    register_packs = True

    def test_get_all(self):
        resp = self.app.get("/v1/config_schemas")
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(
            len(resp.json),
            CONFIG_SCHEMA_COUNT,
            "/v1/config_schemas did not return all schemas.",
        )

    def test_get_one_success(self):
        resp = self.app.get("/v1/config_schemas/dummy_pack_1")
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json["pack"], "dummy_pack_1")
        self.assertIn("api_key", resp.json["attributes"])

    def test_get_one_doesnt_exist(self):
        # Pack exists, schema doesnt
        resp = self.app.get("/v1/config_schemas/dummy_pack_2", expect_errors=True)
        self.assertEqual(resp.status_int, 404)
        self.assertIn(
            "Unable to identify resource with pack_ref ", resp.json["faultstring"]
        )

        # Pack doesn't exist
        ref_or_id = "pack_doesnt_exist"
        resp = self.app.get("/v1/config_schemas/%s" % ref_or_id, expect_errors=True)
        self.assertEqual(resp.status_int, 404)
        # Changed from: 'Unable to find the PackDB instance'
        self.assertTrue(
            'Resource with a ref or id "%s" not found' % ref_or_id
            in resp.json["faultstring"]
        )
