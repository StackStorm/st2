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
import os

from st2common.bootstrap import aliasesregistrar
from st2common.persistence.action import ActionAlias

from st2tests import DbTestCase
from st2tests import fixturesloader

__all__ = ["TestAliasRegistrar"]


ALIASES_FIXTURE_PACK_PATH = os.path.join(
    fixturesloader.get_fixtures_packs_base_path(), "dummy_pack_1"
)
ALIASES_FIXTURE_PATH = os.path.join(ALIASES_FIXTURE_PACK_PATH, "aliases")


class TestAliasRegistrar(DbTestCase):
    def test_alias_registration(self):
        count = aliasesregistrar.register_aliases(pack_dir=ALIASES_FIXTURE_PACK_PATH)
        # expect all files to contain be aliases
        self.assertEqual(count, len(os.listdir(ALIASES_FIXTURE_PATH)))

        action_alias_dbs = ActionAlias.get_all()
        self.assertEqual(action_alias_dbs[0].metadata_file, "aliases/alias1.yaml")
