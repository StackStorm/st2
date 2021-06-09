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

import st2common.bootstrap.triggersregistrar as triggers_registrar
from st2common.persistence.trigger import Trigger
from st2common.persistence.trigger import TriggerType
from st2tests.base import CleanDbTestCase
from st2tests.fixtures.packs.all_packs_glob import PACKS_PATH
from st2tests.fixtures.packs.dummy_pack_1.fixture import (
    PACK_NAME as DUMMY_PACK_1,
    PACK_PATH as DUMMY_PACK_1_PATH,
)

__all__ = ["TriggersRegistrarTestCase"]


class TriggersRegistrarTestCase(CleanDbTestCase):
    def test_register_all_triggers(self):
        trigger_type_dbs = TriggerType.get_all()
        self.assertEqual(len(trigger_type_dbs), 0)

        count = triggers_registrar.register_triggers(packs_base_paths=[PACKS_PATH])
        self.assertEqual(count, 2)

        # Verify TriggerTypeDB and corresponding TriggerDB objects have been created
        trigger_type_dbs = TriggerType.get_all()
        trigger_dbs = Trigger.get_all()
        self.assertEqual(len(trigger_type_dbs), 2)
        self.assertEqual(len(trigger_dbs), 2)

    def test_register_triggers_from_pack(self):
        pack_dir = DUMMY_PACK_1_PATH

        trigger_type_dbs = TriggerType.get_all()
        self.assertEqual(len(trigger_type_dbs), 0)

        count = triggers_registrar.register_triggers(pack_dir=pack_dir)
        self.assertEqual(count, 2)

        # Verify TriggerTypeDB and corresponding TriggerDB objects have been created
        trigger_type_dbs = TriggerType.get_all()
        trigger_dbs = Trigger.get_all()
        self.assertEqual(len(trigger_type_dbs), 2)
        self.assertEqual(len(trigger_dbs), 2)

        self.assertEqual(trigger_type_dbs[0].name, "event_handler")
        self.assertEqual(trigger_type_dbs[0].pack, DUMMY_PACK_1)
        self.assertEqual(trigger_dbs[0].name, "event_handler")
        self.assertEqual(trigger_dbs[0].pack, DUMMY_PACK_1)
        self.assertEqual(trigger_dbs[0].type, "dummy_pack_1.event_handler")

        self.assertEqual(trigger_type_dbs[1].name, "head_sha_monitor")
        self.assertEqual(trigger_type_dbs[1].pack, DUMMY_PACK_1)
        self.assertEqual(trigger_type_dbs[1].payload_schema["type"], "object")
