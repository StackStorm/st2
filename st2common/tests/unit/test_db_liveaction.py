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

from st2common.models.db.liveaction import LiveActionDB
from st2common.models.db.notification import NotificationSchema, NotificationSubSchema
from st2common.persistence.liveaction import LiveAction
from st2common.transport.publishers import PoolPublisher
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.util import date as date_utils

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
        self.assertEqual(retrieved.notify, None)

        # Test update
        self.assertTrue(retrieved.end_timestamp is None)
        retrieved.end_timestamp = date_utils.get_datetime_utc_now()
        updated = LiveAction.add_or_update(retrieved)
        self.assertTrue(updated.end_timestamp == retrieved.end_timestamp)
        # Test delete
        LiveActionModelTest._delete([retrieved])
        try:
            retrieved = LiveAction.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_liveaction_create_with_notify_on_complete_only(self):
        created = LiveActionDB()
        created.action = 'core.local'
        created.description = ''
        created.status = 'running'
        created.parameters = {}

        notify_db = NotificationSchema()
        notify_sub_schema = NotificationSubSchema()
        notify_sub_schema.message = 'Action complete.'
        notify_sub_schema.data = {
            'foo': 'bar',
            'bar': 1,
            'baz': {'k1': 'v1'}
        }
        notify_db.on_complete = notify_sub_schema
        created.notify = notify_db

        saved = LiveActionModelTest._save_liveaction(created)
        retrieved = LiveAction.get_by_id(saved.id)
        self.assertEqual(saved.action, retrieved.action,
                         'Same triggertype was not returned.')
        # Assert notify settings saved are right.
        self.assertEqual(notify_sub_schema.message, retrieved.notify.on_complete.message)
        self.assertDictEqual(notify_sub_schema.data, retrieved.notify.on_complete.data)
        self.assertListEqual(notify_sub_schema.routes, retrieved.notify.on_complete.routes)
        self.assertEqual(retrieved.notify.on_success, None)
        self.assertEqual(retrieved.notify.on_failure, None)

    def test_liveaction_create_with_notify_on_success_only(self):
        created = LiveActionDB()
        created.action = 'core.local'
        created.description = ''
        created.status = 'running'
        created.parameters = {}
        notify_db = NotificationSchema()
        notify_sub_schema = NotificationSubSchema()
        notify_sub_schema.message = 'Action succeeded.'
        notify_sub_schema.data = {
            'foo': 'bar',
            'bar': 1,
            'baz': {'k1': 'v1'}
        }
        notify_db.on_success = notify_sub_schema
        created.notify = notify_db
        saved = LiveActionModelTest._save_liveaction(created)
        retrieved = LiveAction.get_by_id(saved.id)
        self.assertEqual(saved.action, retrieved.action,
                         'Same triggertype was not returned.')

        # Assert notify settings saved are right.
        self.assertEqual(notify_sub_schema.message,
                         retrieved.notify.on_success.message)
        self.assertDictEqual(notify_sub_schema.data, retrieved.notify.on_success.data)
        self.assertListEqual(notify_sub_schema.routes, retrieved.notify.on_success.routes)
        self.assertEqual(retrieved.notify.on_failure, None)
        self.assertEqual(retrieved.notify.on_complete, None)

    def test_liveaction_create_with_notify_both_on_success_and_on_error(self):
        created = LiveActionDB()
        created.action = 'core.local'
        created.description = ''
        created.status = 'running'
        created.parameters = {}
        on_success = NotificationSubSchema(message='Action succeeded.')
        on_failure = NotificationSubSchema(message='Action failed.')
        created.notify = NotificationSchema(on_success=on_success,
                                            on_failure=on_failure)
        saved = LiveActionModelTest._save_liveaction(created)
        retrieved = LiveAction.get_by_id(saved.id)
        self.assertEqual(saved.action, retrieved.action,
                         'Same triggertype was not returned.')
        # Assert notify settings saved are right.
        self.assertEqual(on_success.message, retrieved.notify.on_success.message)
        self.assertEqual(on_failure.message, retrieved.notify.on_failure.message)
        self.assertEqual(retrieved.notify.on_complete, None)

    @staticmethod
    def _save_liveaction(liveaction):
        return LiveAction.add_or_update(liveaction)

    @staticmethod
    def _delete(model_objects):
        for model_object in model_objects:
            model_object.delete()
