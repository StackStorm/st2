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

from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.execution import ActionExecutionDB
from st2common.persistence.execution import ActionExecution
from st2common.transport.publishers import PoolPublisher
from st2common.util import date as date_utils

from st2tests import DbTestCase


INQUIRY_RESULT = {
    'users': [],
    'roles': [],
    'route': 'developers',
    'ttl': 1440,
    'response': {
        'secondfactor': 'supersecretvalue'
    },
    'schema': {
        'type': 'object',
        'properties': {
            'secondfactor': {
                'secret': True,
                'required': True,
                'type': 'string',
                'description': 'Please enter second factor for authenticating to "foo" service'
            }
        }
    }
}

INQUIRY_LIVEACTION = {
    'parameters': {
        'route': 'developers',
        'schema': {
            'type': 'object',
            'properties': {
                'secondfactor': {
                    'secret': True,
                    'required': True,
                    'type': u'string',
                    'description': 'Please enter second factor for authenticating to "foo" service'
                }
            }
        }
    },
    'action': 'core.ask'
}


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ActionExecutionModelTest(DbTestCase):

    def setUp(self):
        created = ActionExecutionDB()
        created.action = {'uid': 'action:core:ask'}
        created.status = 'succeeded'
        created.runner = {'name': 'inquirer'}
        created.liveaction = INQUIRY_LIVEACTION
        created.result = INQUIRY_RESULT

        self.saved = ActionExecutionModelTest._save_execution(created)
        self.retrieved = ActionExecution.get_by_id(self.saved.id)
        self.assertEqual(self.saved.action, self.retrieved.action,
                         'Same action was not returned.')

    def tearDown(self):
        ActionExecutionModelTest._delete([self.retrieved])
        try:
            retrieved = ActionExecution.get_by_id(self.saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_update_execution(self):
        """Test ActionExecutionDb update
        """
        self.assertTrue(self.retrieved.end_timestamp is None)
        self.retrieved.end_timestamp = date_utils.get_datetime_utc_now()
        updated = ActionExecution.add_or_update(self.retrieved)
        self.assertTrue(updated.end_timestamp == self.retrieved.end_timestamp)

    def test_execution_inquiry_secrets(self):
        """Corner case test for Inquiry responses that contain secrets.

        Should properly mask these if the Inquiry is being retrieved
        directly via `execution get` commands.

        TODO(mierdin): Move this once Inquiries get their own data model
        """

        # Test Inquiry response masking is done properly within this model
        masked = self.retrieved.mask_secrets(self.retrieved.to_serializable_dict())
        self.assertEqual(masked['result']['response']['secondfactor'], MASKED_ATTRIBUTE_VALUE)
        self.assertEqual(self.retrieved.result['response']['secondfactor'], "supersecretvalue")

    @staticmethod
    def _save_execution(execution):
        return ActionExecution.add_or_update(execution)

    @staticmethod
    def _delete(model_objects):
        for model_object in model_objects:
            model_object.delete()
