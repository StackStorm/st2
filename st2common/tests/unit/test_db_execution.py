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

RESPOND_LIVEACTION = {
    'parameters': {
        'response': {
            'secondfactor': 'omgsupersecret',
        }
    },
    'action': 'st2.inquiry.respond'
}

ACTIONEXECUTIONS = {
    "execution_1": {
        'action': {'uid': 'action:core:ask'},
        'status': 'succeeded',
        'runner': {'name': 'inquirer'},
        'liveaction': INQUIRY_LIVEACTION,
        'result': INQUIRY_RESULT
    },
    "execution_2": {
        'action': {'uid': 'action:st2:inquiry.respond'},
        'status': 'succeeded',
        'runner': {'name': 'python-script'},
        'liveaction': RESPOND_LIVEACTION,
        'result': {
            'exit_code': 0,
            'result': None,
            'stderr': '',
            'stdout': ''
        }
    }
}


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class ActionExecutionModelTest(DbTestCase):

    def setUp(self):

        self.executions = {}

        for name, execution in ACTIONEXECUTIONS.items():

            created = ActionExecutionDB()
            created.action = execution['action']
            created.status = execution['status']
            created.runner = execution['runner']
            created.liveaction = execution['liveaction']
            created.result = execution['result']

            saved = ActionExecutionModelTest._save_execution(created)
            retrieved = ActionExecution.get_by_id(saved.id)
            self.assertEqual(saved.action, retrieved.action,
                             'Same action was not returned.')

            self.executions[name] = retrieved

    def tearDown(self):

        for name, execution in self.executions.items():
            ActionExecutionModelTest._delete([execution])
            try:
                retrieved = ActionExecution.get_by_id(execution.id)
            except StackStormDBObjectNotFoundError:
                retrieved = None
            self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    def test_update_execution(self):
        """Test ActionExecutionDb update
        """
        self.assertTrue(self.executions['execution_1'].end_timestamp is None)
        self.executions['execution_1'].end_timestamp = date_utils.get_datetime_utc_now()
        updated = ActionExecution.add_or_update(self.executions['execution_1'])
        self.assertTrue(updated.end_timestamp == self.executions['execution_1'].end_timestamp)

    def test_execution_inquiry_secrets(self):
        """Corner case test for Inquiry responses that contain secrets.

        Should properly mask these if the Inquiry is being retrieved
        directly via `execution get` commands.

        TODO(mierdin): Move this once Inquiries get their own data model
        """

        # Test Inquiry response masking is done properly within this model
        masked = self.executions['execution_1'].mask_secrets(
            self.executions['execution_1'].to_serializable_dict()
        )
        self.assertEqual(masked['result']['response']['secondfactor'], MASKED_ATTRIBUTE_VALUE)
        self.assertEqual(
            self.executions['execution_1'].result['response']['secondfactor'],
            "supersecretvalue"
        )

    def test_execution_inquiry_response_action(self):
        """Test that the response parameters for any `st2.inquiry.respond` executions are masked

        We aren't bothering to get the inquiry schema in the `st2.inquiry.respond` action,
        so we mask all response values. This test ensures this happens.
        """

        masked = self.executions['execution_2'].mask_secrets(
            self.executions['execution_2'].to_serializable_dict()
        )
        for value in masked['parameters']['response'].values():
            self.assertEqual(value, MASKED_ATTRIBUTE_VALUE)

    @staticmethod
    def _save_execution(execution):
        return ActionExecution.add_or_update(execution)

    @staticmethod
    def _delete(model_objects):
        for model_object in model_objects:
            model_object.delete()
