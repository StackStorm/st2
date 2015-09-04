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

from st2tests.base import CleanDbTestCase
from st2common.models.db.pack import PackDB
from st2common.models.db.action import ActionDB
from st2common.persistence.pack import Pack
from st2common.persistence.action import Action


class UIDMixinTestCase(CleanDbTestCase):
    def test_get_uid(self):
        pack_1_db = PackDB(ref='test_pack')
        pack_2_db = PackDB(ref='examples')

        self.assertEqual(pack_1_db.get_uid(), 'pack:test_pack')
        self.assertEqual(pack_2_db.get_uid(), 'pack:examples')

        action_1_db = ActionDB(pack='examples', name='my_action', ref='examples.my_action')
        action_2_db = ActionDB(pack='core', name='local', ref='core.local')
        self.assertEqual(action_1_db.get_uid(), 'action:examples:my_action')
        self.assertEqual(action_2_db.get_uid(), 'action:core:local')

    def test_uid_is_populated_on_save(self):
        pack_1_db = PackDB(ref='test_pack', name='test', description='foo', version='1.0',
                           author='dev', email='test@example.com')
        pack_1_db = Pack.add_or_update(pack_1_db)
        pack_1_db.reload()

        self.assertEqual(pack_1_db.uid, 'pack:test_pack')

        action_1_db = ActionDB(name='local', pack='core', ref='core.local', entry_point='',
                               runner_type={'name': 'local-shell-cmd'})
        action_1_db = Action.add_or_update(action_1_db)
        action_1_db.reload()

        self.assertEqual(action_1_db.uid, 'action:core:local')
