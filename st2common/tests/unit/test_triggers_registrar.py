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

import os

import st2common.bootstrap.triggersregistrar as triggers_registrar
from st2common.persistence.trigger import Trigger
from st2common.persistence.trigger import TriggerType
from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import get_fixtures_packs_base_path

__all__ = [
    'TriggersRegistrarTestCase'
]


class TriggersRegistrarTestCase(CleanDbTestCase):
    def test_register_all_triggers(self):
        trigger_type_dbs = TriggerType.get_all()
        self.assertEqual(len(trigger_type_dbs), 0)

        packs_base_path = get_fixtures_packs_base_path()
        count = triggers_registrar.register_triggers(packs_base_paths=[packs_base_path])
        self.assertEqual(count, 2)

        # Verify TriggerTypeDB and corresponding TriggerDB objects have been created
        trigger_type_dbs = TriggerType.get_all()
        trigger_dbs = Trigger.get_all()
        self.assertEqual(len(trigger_type_dbs), 2)
        self.assertEqual(len(trigger_dbs), 2)

    def test_register_triggers_from_pack(self):
        base_path = get_fixtures_packs_base_path()
        pack_dir = os.path.join(base_path, 'dummy_pack_1')

        trigger_type_dbs = TriggerType.get_all()
        self.assertEqual(len(trigger_type_dbs), 0)

        count = triggers_registrar.register_triggers(pack_dir=pack_dir)
        self.assertEqual(count, 2)

        # Verify TriggerTypeDB and corresponding TriggerDB objects have been created
        trigger_type_dbs = TriggerType.get_all()
        trigger_dbs = Trigger.get_all()
        self.assertEqual(len(trigger_type_dbs), 2)
        self.assertEqual(len(trigger_dbs), 2)

        self.assertEqual(trigger_type_dbs[0].name, 'event_handler')
        self.assertEqual(trigger_type_dbs[0].pack, 'dummy_pack_1')
        self.assertEqual(trigger_dbs[0].name, 'event_handler')
        self.assertEqual(trigger_dbs[0].pack, 'dummy_pack_1')
        self.assertEqual(trigger_dbs[0].type, 'dummy_pack_1.event_handler')

        self.assertEqual(trigger_type_dbs[1].name, 'head_sha_monitor')
        self.assertEqual(trigger_type_dbs[1].pack, 'dummy_pack_1')
        self.assertEqual(trigger_type_dbs[1].payload_schema['type'], 'object')
