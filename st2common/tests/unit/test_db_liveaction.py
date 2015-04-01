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

import datetime

import mock

from st2common.models.db.action import LiveActionDB, NotificationSchema, NotificationSubSchema
from st2common.persistence.action import LiveAction
from st2common.transport.publishers import PoolPublisher
from st2common.util import isotime

from st2tests import DbTestCase


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class LiveActionModelTest(DbTestCase):

    def test_liveaction_crud_no_notify(self):
        created = LiveActionDB()
        created.action = 'core.local'
        created.description = ''
        created.status = 'running'
        created.parameters = {}
        saved = LiveActionModelTest._save_liveaction(created)
        retrieved = LiveAction.get_by_id(saved.id)
        self.assertEqual(saved.action, retrieved.action,
                         'Same triggertype was not returned.')

        # Test update
        self.assertTrue(retrieved.end_timestamp is None)
        retrieved.end_timestamp = isotime.add_utc_tz(datetime.datetime.utcnow())
        updated = LiveAction.add_or_update(retrieved)
        self.assertTrue(updated.end_timestamp == retrieved.end_timestamp)

        # Test delete
        LiveActionModelTest._delete([retrieved])
        try:
            retrieved = LiveAction.get_by_id(saved.id)
        except ValueError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_liveaction_create_with_notify(self):
        created = LiveActionDB()
        created.action = 'core.local'
        created.description = ''
        created.status = 'running'
        created.parameters = {}
        notify_db = NotificationSchema()
        notify_sub_schema = NotificationSubSchema()
        notify_sub_schema.message = 'Foo'
        notify_sub_schema.data = {
            'foo': 'bar',
            'bar': 1,
            'baz': {'k1': 'v1'}
        }
        notify_db.on_success = notify_sub_schema
        created.notify = notify_db

        print('Created.notify: %s' % created.notify)
        saved = LiveActionModelTest._save_liveaction(created)
        retrieved = LiveAction.get_by_id(saved.id)
        print('Retrieved: %s' % retrieved)
        self.assertEqual(saved.action, retrieved.action,
                         'Same triggertype was not returned.')

    @staticmethod
    def _save_liveaction(liveaction):
        return LiveAction.add_or_update(liveaction)

    @staticmethod
    def _delete(model_objects):
        for model_object in model_objects:
            model_object.delete()
