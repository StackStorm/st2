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

import eventlet

from st2common.constants.triggers import WEBHOOK_TRIGGER_TYPE, WEBHOOK_TRIGGER_TYPES
from st2common.models.api.trigger import TriggerAPI
from st2common.services.triggerwatcher import TriggerWatcher
from st2common.transport.reactor import TriggerCUDPublisher
from st2common.transport import utils as transport_utils
from st2common.transport.bootstrap_utils import register_exchanges
from st2tests.base import CleanDbTestCase, EventletTestCase, IntegrationTestCase
import st2tests.config as st2tests_config
st2tests_config.parse_args()


class TestTriggerWatcher(CleanDbTestCase, EventletTestCase, IntegrationTestCase):
    CREATED = 0

    @classmethod
    def setUpClass(cls):
        super(TestTriggerWatcher, cls).setUpClass()
        register_exchanges()
        return

    def test_multiple_trigger_watchers(self):
        # In this test, we spin multiple trigger watchers. There was a bug in queue name not
        # being unique for each trigger watcher which resulted in lock issues in rabbitmq.
        # Queue names now contain a UUID (length limited) string.

        watcher_1 = TriggerWatcher(create_handler=self._create_handler,
                                   update_handler=self._update_handler,
                                   delete_handler=self._delete_handler,
                                   trigger_types=WEBHOOK_TRIGGER_TYPES.keys(),
                                   queue_suffix='itests', exclusive=True)
        watcher_2 = TriggerWatcher(create_handler=self._create_handler,
                                   update_handler=self._update_handler,
                                   delete_handler=self._delete_handler,
                                   trigger_types=WEBHOOK_TRIGGER_TYPES.keys(),
                                   queue_suffix='itests', exclusive=True)

        watcher_1.start()
        watcher_2.start()
        print('Watchers started')

        publisher = TriggerCUDPublisher(urls=transport_utils.get_messaging_urls())
        test_webhook_trigger_api = {
            'name': 'my.test.webhook.trigger',
            'pack': 'dumb_tests',
            'type': WEBHOOK_TRIGGER_TYPE,
            'parameters': {
                'url': '/dumb_tests'
            }
        }
        test_webhook_trigger_db = TriggerAPI.to_model(TriggerAPI(**test_webhook_trigger_api))
        publisher.publish_create(payload=test_webhook_trigger_db)
        eventlet.sleep(30)

    def _create_handler(self, trigger):
        print('Called')
        TestTriggerWatcher.CREATED += 1

    def _delete_handler(self, trigger):
        pass

    def _update_handler(self, trigger):
        pass
