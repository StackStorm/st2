# -*- coding: UTF-8 -*-
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

from __future__ import absolute_import

import six
import mock
import requests
from mock import call

from mistralclient.api.v2 import action_executions
from oslo_config import cfg

# XXX: actionsensor import depends on config being setup.
import st2tests.config as tests_config
from six.moves import range
tests_config.parse_args()

from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.liveaction import LiveAction
from st2common.runners import base as runners
from st2common.services import action as action_service
from st2common.transport.liveaction import LiveActionPublisher
from st2common.transport.publishers import CUDPublisher
from st2common.util import loader
from st2tests import DbTestCase
from st2tests import fixturesloader
from st2tests.mocks.liveaction import MockLiveActionPublisher


MISTRAL_RUNNER_NAME = 'mistral_v2'
TEST_PACK = 'mistral_tests'
TEST_PACK_PATH = fixturesloader.get_fixtures_packs_base_path() + '/' + TEST_PACK

PACKS = [
    TEST_PACK_PATH,
    fixturesloader.get_fixtures_packs_base_path() + '/core'
]

if six.PY2:
    NON_EMPTY_RESULT = 'non-empty'
else:
    NON_EMPTY_RESULT = u'non-empty'


@mock.patch.object(
    CUDPublisher,
    'publish_update',
    mock.MagicMock(return_value=None))
@mock.patch.object(
    CUDPublisher,
    'publish_create',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_create))
@mock.patch.object(
    LiveActionPublisher,
    'publish_state',
    mock.MagicMock(side_effect=MockLiveActionPublisher.publish_state))
class MistralRunnerCallbackTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(MistralRunnerCallbackTest, cls).setUpClass()

        # Override the retry configuration here otherwise st2tests.config.parse_args
        # in DbTestCase.setUpClass will reset these overrides.
        cfg.CONF.set_override('retry_exp_msec', 100, group='mistral')
        cfg.CONF.set_override('retry_exp_max_msec', 200, group='mistral')
        cfg.CONF.set_override('retry_stop_max_msec', 200, group='mistral')
        cfg.CONF.set_override('api_url', 'http://0.0.0.0:9101', group='auth')

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False,
            fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

        # Get an instance of the callback module and reference to mistral status map
        cls.callback_module = loader.register_callback_module(MISTRAL_RUNNER_NAME)
        cls.callback_class = cls.callback_module.get_instance()
        cls.status_map = cls.callback_module.STATUS_MAP

    @classmethod
    def get_runner_class(cls, package_name, module_name):
        return runners.get_runner(package_name, module_name).__class__

    def get_liveaction_instance(self, status=None, result=None):
        callback = {
            'source': MISTRAL_RUNNER_NAME,
            'url': 'http://127.0.0.1:8989/v2/action_executions/12345'
        }

        liveaction = LiveActionDB(
            action='core.local',
            parameters={'cmd': 'uname -a'},
            callback=callback,
            context=dict()
        )

        if status:
            liveaction.status = status

        if result:
            liveaction.result = result

        return liveaction

    def test_callback_handler_status_map(self):
        # Ensure all StackStorm status are mapped otherwise leads to zombie workflow.
        self.assertListEqual(sorted(self.status_map.keys()),
                             sorted(action_constants.LIVEACTION_STATUSES))

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_text(self):
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = '<html></html>'
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output='<html></html>'
        )

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_dict(self):
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = {'a': 1}
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output='{"a": 1}'
        )

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_json_str(self):
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = '{"a": 1}'
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output='{"a": 1}'
        )

        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = "{'a': 1}"
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output='{"a": 1}'
        )

        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = u"{'a': 1}"
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output='{"a": 1}'
        )

        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = "{u'a': u'xyz'}"
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output='{"a": "xyz"}'
        )

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_list(self):
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = ["a", "b", "c"]
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output='["a", "b", "c"]'
        )

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_list_str(self):
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = '["a", "b", "c"]'
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output='["a", "b", "c"]'
        )

        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = u'["a", "b", "c"]'
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output='["a", "b", "c"]'
        )

        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = '[u"a", "b", "c"]'
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output='["a", "b", "c"]'
        )

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_unicode_str(self):
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = '什麼'
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        if six.PY2:
            expected_output = '\\u4ec0\\u9ebc'
        else:
            expected_output = '什麼'

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output=expected_output
        )

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_unicode_encoded_as_ascii_str(self):
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = '\u4ec0\u9ebc'
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        if six.PY2:
            expected_output = '\\\\u4ec0\\\\u9ebc'
        else:
            expected_output = '什麼'

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output=expected_output
        )

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_unicode_encoded_as_type(self):
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = u'\u4ec0\u9ebc'
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        if six.PY2:
            expected_output = '\\u4ec0\\u9ebc'
        else:
            expected_output = '什麼'

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output=expected_output
        )

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_list_with_unicode_str(self):
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = ['\u4ec0\u9ebc']
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        if six.PY2:
            expected_output = '["\\\\u4ec0\\\\u9ebc"]'
        else:
            expected_output = '["\\u4ec0\\u9ebc"]'

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output=expected_output
        )

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_list_with_unicode_type(self):
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = [u'\u4ec0\u9ebc']
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        if six.PY2:
            expected_output = '["\\\\u4ec0\\\\u9ebc"]'
        else:
            expected_output = '["\\u4ec0\\u9ebc"]'

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output=expected_output
        )

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_dict_with_unicode_str(self):
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = {'a': '\u4ec0\u9ebc'}
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        if six.PY2:
            expected_output = '{"a": "\\\\u4ec0\\\\u9ebc"}'
        else:
            expected_output = '{"a": "\\u4ec0\\u9ebc"}'

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output=expected_output
        )

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_handler_with_result_as_dict_with_unicode_type(self):
        status = action_constants.LIVEACTION_STATUS_SUCCEEDED
        result = {'a': u'\u4ec0\u9ebc'}
        liveaction = self.get_liveaction_instance(status, result)
        self.callback_class.callback(liveaction)

        if six.PY2:
            expected_output = '{"a": "\\\\u4ec0\\\\u9ebc"}'
        else:
            expected_output = '{"a": "\\u4ec0\\u9ebc"}'

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345',
            state='SUCCESS',
            output=expected_output
        )

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_success_state(self):
        local_runner_cls = self.get_runner_class('local_runner', 'local_shell_command_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_SUCCEEDED, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)
        expected_mistral_status = self.status_map[local_run_result[0]]
        liveaction = self.get_liveaction_instance()
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345', state=expected_mistral_status, output=NON_EMPTY_RESULT)

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_incomplete_state(self):
        local_runner_cls = self.get_runner_class('local_runner', 'local_shell_command_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_RUNNING, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)
        liveaction = self.get_liveaction_instance()
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        self.assertEqual(liveaction.status, local_run_result[0])
        self.assertFalse(action_executions.ActionExecutionManager.update.called)

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_canceling_state(self):
        local_runner_cls = self.get_runner_class('local_runner', 'local_shell_command_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_CANCELING, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)
        local_cancel_result = (action_constants.LIVEACTION_STATUS_CANCELING, NON_EMPTY_RESULT, None)
        local_runner_cls.cancel = mock.Mock(return_value=local_cancel_result)
        liveaction = self.get_liveaction_instance()
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        self.assertEqual(liveaction.status, local_cancel_result[0])

        action_executions.ActionExecutionManager.update.assert_not_called()

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_canceled_state(self):
        local_runner_cls = self.get_runner_class('local_runner', 'local_shell_command_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_CANCELED, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)
        expected_mistral_status = self.status_map[local_run_result[0]]
        liveaction = self.get_liveaction_instance()
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        self.assertEqual(liveaction.status, local_run_result[0])

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345', state=expected_mistral_status, output=NON_EMPTY_RESULT)

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_pausing_state(self):
        local_runner_cls = self.get_runner_class('local_runner', 'local_shell_command_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_PAUSING, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)
        local_pause_result = (action_constants.LIVEACTION_STATUS_PAUSING, NON_EMPTY_RESULT, None)
        local_runner_cls.pause = mock.Mock(return_value=local_pause_result)
        liveaction = self.get_liveaction_instance()
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        self.assertEqual(liveaction.status, local_pause_result[0])

        action_executions.ActionExecutionManager.update.assert_not_called()

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_paused_state(self):
        local_runner_cls = self.get_runner_class('local_runner', 'local_shell_command_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_PAUSED, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)
        expected_mistral_status = self.status_map[local_run_result[0]]
        liveaction = self.get_liveaction_instance()
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        self.assertEqual(liveaction.status, local_run_result[0])

        action_executions.ActionExecutionManager.update.assert_called_with(
            '12345', state=expected_mistral_status, output=NON_EMPTY_RESULT)

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(return_value=None))
    def test_callback_resuming_state(self):
        local_runner_cls = self.get_runner_class('local_runner', 'local_shell_command_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_RESUMING, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)
        local_resume_result = (action_constants.LIVEACTION_STATUS_RUNNING, NON_EMPTY_RESULT, None)
        local_runner_cls.resume = mock.Mock(return_value=local_resume_result)
        liveaction = self.get_liveaction_instance()
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))

        self.assertEqual(liveaction.status, local_resume_result[0])
        self.assertFalse(action_executions.ActionExecutionManager.update.called)

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(side_effect=[
            requests.exceptions.ConnectionError(),
            None]))
    def test_callback_retry(self):
        local_runner_cls = self.get_runner_class('local_runner', 'local_shell_command_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_SUCCEEDED, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)
        liveaction = self.get_liveaction_instance()
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        calls = [call('12345', state='SUCCESS', output=NON_EMPTY_RESULT) for i in range(0, 2)]
        action_executions.ActionExecutionManager.update.assert_has_calls(calls)

    @mock.patch.object(
        action_executions.ActionExecutionManager, 'update',
        mock.MagicMock(side_effect=[
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            None]))
    def test_callback_retry_exhausted(self):
        local_runner_cls = self.get_runner_class('local_runner', 'local_shell_command_runner')
        local_run_result = (action_constants.LIVEACTION_STATUS_SUCCEEDED, NON_EMPTY_RESULT, None)
        local_runner_cls.run = mock.Mock(return_value=local_run_result)
        liveaction = self.get_liveaction_instance()
        liveaction, execution = action_service.request(liveaction)
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_SUCCEEDED)

        # This test initially setup mock for action_executions.ActionExecutionManager.update
        # to fail the first 4 times and return success on the 5th times. The max attempts
        # is set to 3. We expect only 3 calls to pass thru the update method.
        calls = [call('12345', state='SUCCESS', output=NON_EMPTY_RESULT) for i in range(0, 2)]
        action_executions.ActionExecutionManager.update.assert_has_calls(calls)
