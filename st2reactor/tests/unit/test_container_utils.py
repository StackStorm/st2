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

from st2common.models.db.reactor import TriggerDB
from st2common.transport.publishers import PoolPublisher
import st2reactor.container.utils as container_utils
from st2tests.base import CleanDbTestCase

MOCK_TRIGGER_TYPE = {}
MOCK_TRIGGER_TYPE['id'] = 'trigger-type-test.id'
MOCK_TRIGGER_TYPE['name'] = 'trigger-type-test.name'
MOCK_TRIGGER_TYPE['pack'] = 'dummy_pack_1'
MOCK_TRIGGER_TYPE['parameters_schema'] = {}
MOCK_TRIGGER_TYPE['payload_schema'] = {}

MOCK_TRIGGER = TriggerDB()
MOCK_TRIGGER.id = 'trigger-test.id'
MOCK_TRIGGER.name = 'trigger-test.name'
MOCK_TRIGGER.pack = 'dummy_pack_1'
MOCK_TRIGGER.parameters = {}
MOCK_TRIGGER.type = 'dummy_pack_1.trigger-type-test.name'


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ContainerUtilsTest(CleanDbTestCase):

    def test_create_trigger_instance_invalid_trigger(self):
        trigger_instance = 'dummy_pack.footrigger'
        instance = container_utils.create_trigger_instance(trigger_instance, {}, None)
        self.assertTrue(instance is None)
