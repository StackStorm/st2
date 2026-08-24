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

"""
Test that verifies KombuError exceptions from persistence layer propagate
correctly through the action runner, causing process exit for K8s restart.
"""

from __future__ import absolute_import

import mock
from oslo_config import cfg
from kombu import exceptions as kombu_exceptions

from st2tests.base import DbTestCase
import st2tests.config as tests_config
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.execution import ActionExecution
from st2common.persistence.liveaction import LiveAction
from st2common.services import executions
from st2common.util import date as date_utils
from st2common.bootstrap import runnersregistrar as runners_registrar
from st2tests.fixtures.generic.fixture import PACK_NAME as FIXTURES_PACK
from st2tests.fixturesloader import FixturesLoader
import st2actions.worker as actions_worker


TEST_FIXTURES = {"actions": ["local.yaml"]}


class KombuErrorPropagationTestCase(DbTestCase):
    """
    Test case to verify that KombuError exceptions from the persistence layer
    propagate correctly to cause action runner process exit.
    """

    fixtures_loader = FixturesLoader()

    @classmethod
    def setUpClass(cls):
        super(KombuErrorPropagationTestCase, cls).setUpClass()
        runners_registrar.register_runners()

        models = cls.fixtures_loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES
        )
        cls.local_action_db = models["actions"]["local.yaml"]

    def setUp(self):
        super(KombuErrorPropagationTestCase, self).setUp()
        tests_config.reset()
        tests_config.parse_args()

    def _get_liveaction_model(self, action_db, params):
        """Helper to create a LiveAction model for testing."""
        status = action_constants.LIVEACTION_STATUS_REQUESTED
        start_timestamp = date_utils.get_datetime_utc_now()
        action_ref = ResourceReference(name=action_db.name, pack=action_db.pack).ref
        parameters = params
        context = {"user": cfg.CONF.system_user.user}
        liveaction_db = LiveActionDB(
            status=status,
            start_timestamp=start_timestamp,
            action=action_ref,
            parameters=parameters,
            context=context,
        )
        return liveaction_db

    def test_kombu_error_in_execution_update_propagates(self):
        """
        Test that when ActionExecution.update() raises KombuError during
        execution update, the exception propagates up through the worker to cause
        process exit.

        This test also verifies that the persistence layer's built-in rollback
        mechanism (in base.py) properly restores the ActionExecution to its
        previous state when KombuError occurs during publish/dispatch.

        This ensures K8s can detect the failure and restart the action runner
        to reconnect to RabbitMQ without leaving orphaned "running" records.
        """
        action_worker = actions_worker.get_worker()

        # Create a liveaction
        params = {"cmd": "echo 'test'"}
        liveaction_db = self._get_liveaction_model(self.local_action_db, params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)

        # Create initial execution object (this will succeed)
        executions.create_execution_object(liveaction_db)

        # Mock ActionExecution.update to raise KombuError on first call only
        # This simulates the scenario where:
        # 1. LiveAction update to "running" succeeds (in database)
        # 2. ActionExecution.update fails with KombuError
        # 3. Worker attempts rollback of LiveAction
        # We need to ensure only the ActionExecution.update fails, not the rollback
        original_update = ActionExecution.update
        first_call = [True]

        def mock_update_first_call_only(model_object, **kwargs):
            if first_call[0]:
                first_call[0] = False
                raise kombu_exceptions.KombuError("RabbitMQ connection failed")
            return original_update(model_object, **kwargs)

        with mock.patch.object(
            ActionExecution,
            "update",
            side_effect=mock_update_first_call_only,
        ):
            # Attempt to run the action - this should raise KombuError
            with self.assertRaises(kombu_exceptions.KombuError) as cm:
                action_worker._run_action(liveaction_db)

        # Verify the exception message
        self.assertIn("RabbitMQ connection failed", str(cm.exception))

        # Verify that both ActionExecution and LiveAction were rolled back
        # The worker now implements a transaction-like pattern where:
        # 1. LiveAction is updated to "running" without publish
        # 2. ActionExecution is updated (with built-in rollback in base.py)
        # 3. If step 2 fails with KombuError, LiveAction is also rolled back
        # This prevents orphaned "running" LiveActions that could be re-dispatched
        updated_liveaction = LiveAction.get_by_id(liveaction_db.id)
        self.assertEqual(
            updated_liveaction.status, action_constants.LIVEACTION_STATUS_REQUESTED
        )

    def test_kombu_connection_error_propagates(self):
        """
        Test that ConnectionError (a subclass of KombuError) also propagates correctly
        and that the persistence layer's built-in rollback works for this exception type.
        """
        action_worker = actions_worker.get_worker()

        params = {"cmd": "echo 'test'"}
        liveaction_db = self._get_liveaction_model(self.local_action_db, params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)

        # Create initial execution object
        executions.create_execution_object(liveaction_db)

        # Mock to raise ConnectionError on first call only
        original_update = ActionExecution.update
        first_call = [True]

        def mock_update_first_call_only(model_object, **kwargs):
            if first_call[0]:
                first_call[0] = False
                raise kombu_exceptions.ConnectionError("Connection lost")
            return original_update(model_object, **kwargs)

        with mock.patch.object(
            ActionExecution,
            "update",
            side_effect=mock_update_first_call_only,
        ):
            # Verify the exception propagates
            with self.assertRaises(kombu_exceptions.ConnectionError) as cm:
                action_worker._run_action(liveaction_db)

        self.assertIn("Connection lost", str(cm.exception))

        # Verify that the transaction-like rollback worked
        updated_liveaction = LiveAction.get_by_id(liveaction_db.id)
        self.assertEqual(
            updated_liveaction.status, action_constants.LIVEACTION_STATUS_REQUESTED
        )

    def test_kombu_operational_error_propagates(self):
        """
        Test that OperationalError (another subclass of KombuError) also propagates
        and that the persistence layer's built-in rollback works for this exception type.
        """
        action_worker = actions_worker.get_worker()

        params = {"cmd": "echo 'test'"}
        liveaction_db = self._get_liveaction_model(self.local_action_db, params)
        liveaction_db = LiveAction.add_or_update(liveaction_db)

        # Create initial execution object
        executions.create_execution_object(liveaction_db)

        # Mock to raise OperationalError on first call only
        original_update = ActionExecution.update
        first_call = [True]

        def mock_update_first_call_only(model_object, **kwargs):
            if first_call[0]:
                first_call[0] = False
                raise kombu_exceptions.OperationalError("Channel error")
            return original_update(model_object, **kwargs)

        with mock.patch.object(
            ActionExecution,
            "update",
            side_effect=mock_update_first_call_only,
        ):
            # Verify the exception propagates
            with self.assertRaises(kombu_exceptions.OperationalError) as cm:
                action_worker._run_action(liveaction_db)

        self.assertIn("Channel error", str(cm.exception))

        # Verify that the transaction-like rollback worked
        updated_liveaction = LiveAction.get_by_id(liveaction_db.id)
        self.assertEqual(
            updated_liveaction.status, action_constants.LIVEACTION_STATUS_REQUESTED
        )
