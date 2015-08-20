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

import bson
import mock

from st2common.constants.triggers import TIMER_TRIGGER_TYPES
from st2common.models.db.trigger import TriggerDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.trigger import TriggerType
from st2common.persistence.trigger import Trigger
from st2reactor.timer.base import St2Timer
from st2tests.base import CleanDbTestCase


class St2TimerTestCase(CleanDbTestCase):
    def test_trigger_types_are_registered_on_start(self):
        timer = St2Timer()
        timer._scheduler = mock.Mock()

        # Verify there are no TriggerType in the db when we start
        self.assertItemsEqual(TriggerType.get_all(), [])

        timer.start()

        # Verify TriggerType objects have been created
        trigger_type_dbs = TriggerType.get_all()
        self.assertEqual(len(trigger_type_dbs), len(TIMER_TRIGGER_TYPES))

        timer_trigger_type_refs = TIMER_TRIGGER_TYPES.keys()

        for trigger_type in trigger_type_dbs:
            ref = ResourceReference(pack=trigger_type.pack, name=trigger_type.name).ref
            self.assertTrue(ref in timer_trigger_type_refs)

    def test_existing_rules_are_loaded_on_start(self):
        # Assert that we dispatch message for every existing Trigger object
        St2Timer._handle_create_trigger = mock.Mock()

        timer = St2Timer()
        timer._scheduler = mock.Mock()
        timer._trigger_watcher.run = mock.Mock()

        # Verify there are no Trigger and TriggerType in the db wh:w
        self.assertItemsEqual(Trigger.get_all(), [])
        self.assertItemsEqual(TriggerType.get_all(), [])

        # Add a dummy timer Trigger object
        type_ = TIMER_TRIGGER_TYPES.keys()[0]
        parameters = {'unit': 'seconds', 'delta': 1000}
        trigger_db = TriggerDB(id=bson.ObjectId(), name='test_trigger_1', pack='dummy',
                               type=type_, parameters=parameters)
        trigger_db = Trigger.add_or_update(trigger_db)

        # Verify object has been added
        self.assertEqual(len(Trigger.get_all()), 1)

        timer.start()
        timer._trigger_watcher._load_thread.wait()

        # Verify handlers are called
        timer._handle_create_trigger.assert_called_with(trigger_db)

    @mock.patch('st2common.transport.reactor.TriggerDispatcher.dispatch')
    def test_timer_trace_tag_creation(self, dispatch_mock):
        timer = St2Timer()
        timer._scheduler = mock.Mock()
        timer._trigger_watcher = mock.Mock()

        # Add a dummy timer Trigger object
        type_ = TIMER_TRIGGER_TYPES.keys()[0]
        parameters = {'unit': 'seconds', 'delta': 1}
        trigger_db = TriggerDB(name='test_trigger_1', pack='dummy', type=type_,
                               parameters=parameters)
        timer.add_trigger(trigger_db)
        timer._emit_trigger_instance(trigger=trigger_db)

        self.assertEqual(dispatch_mock.call_args[1]['trace_context'].trace_tag,
                         '%s-%s' % (TIMER_TRIGGER_TYPES[type_]['name'], trigger_db.name))
