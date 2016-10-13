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

import mock

from st2common.transport.publishers import PoolPublisher
from st2reactor.container.utils import create_trigger_instance
from st2common.persistence.trigger import Trigger
from st2common.models.db.trigger import TriggerDB
from st2tests.base import CleanDbTestCase


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ContainerUtilsTest(CleanDbTestCase):
    def setUp(self):
        super(ContainerUtilsTest, self).setUp()

        # Insert mock TriggerDB
        trigger_db = TriggerDB(name='name1', pack='pack1', type='type1',
                               parameters={'a': 1, 'b': '2', 'c': 'foo'})
        self.trigger_db = Trigger.add_or_update(trigger_db)

    def test_create_trigger_instance_invalid_trigger(self):
        trigger_instance = 'dummy_pack.footrigger'
        instance = create_trigger_instance(trigger=trigger_instance, payload={},
                                           occurrence_time=None)
        self.assertTrue(instance is None)

    def test_create_trigger_instance_success(self):
        # Here we test trigger instance creation using various ways to look up corresponding
        # TriggerDB object
        payload = {}
        occurrence_time = None

        # TriggerDB look up by id
        trigger = {'id': self.trigger_db.id}
        trigger_instance_db = create_trigger_instance(trigger=trigger, payload=payload,
                                                      occurrence_time=occurrence_time)
        self.assertEqual(trigger_instance_db.trigger, 'pack1.name1')

        # Object doesn't exist (invalid id)
        trigger = {'id': '5776aa2b0640fd2991b15987'}
        trigger_instance_db = create_trigger_instance(trigger=trigger, payload=payload,
                                                      occurrence_time=occurrence_time)
        self.assertEqual(trigger_instance_db, None)

        # TriggerDB look up by uid
        trigger = {'uid': self.trigger_db.uid}
        trigger_instance_db = create_trigger_instance(trigger=trigger, payload=payload,
                                                      occurrence_time=occurrence_time)
        self.assertEqual(trigger_instance_db.trigger, 'pack1.name1')

        trigger = {'uid': 'invaliduid'}
        trigger_instance_db = create_trigger_instance(trigger=trigger, payload=payload,
                                                      occurrence_time=occurrence_time)
        self.assertEqual(trigger_instance_db, None)

        # TriggerDB look up by type and parameters (last resort)
        trigger = {'type': 'pack1.name1', 'parameters': self.trigger_db.parameters}
        trigger_instance_db = create_trigger_instance(trigger=trigger, payload=payload,
                                                      occurrence_time=occurrence_time)

        trigger = {'type': 'pack1.name1', 'parameters': {}}
        trigger_instance_db = create_trigger_instance(trigger=trigger, payload=payload,
                                                      occurrence_time=occurrence_time)
        self.assertEqual(trigger_instance_db, None)
