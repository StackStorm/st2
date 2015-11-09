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

from st2actions.runners import announcementrunner
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.models.api.trace import TraceContext
from base import RunnerTestCase
import st2tests.config as tests_config


mock_dispatcher = mock.Mock()


@mock.patch('st2common.transport.announcement.AnnouncementDispatcher.dispatch')
class AnnouncementRunnerTestCase(RunnerTestCase):

    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    def test_runner_creation(self, dispatch):
        runner = announcementrunner.get_runner()
        self.assertTrue(runner is not None, 'Creation failed. No instance.')
        self.assertEqual(type(runner), announcementrunner.AnnouncementRunner,
                         'Creation failed. No instance.')
        self.assertEqual(runner._dispatcher.dispatch, dispatch)

    def test_announcement(self, dispatch):
        runner = announcementrunner.get_runner()
        runner.runner_parameters = {
            'experimental': True,
            'route': 'general'
        }
        runner.liveaction = mock.Mock(context={})

        runner.pre_run()
        (status, result, _) = runner.run({'test': 'passed'})

        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(result is not None)
        self.assertEqual(result['test'], 'passed')
        dispatch.assert_called_once_with('general', payload={'test': 'passed'},
                                         trace_context=None)

    def test_announcement_no_experimental(self, dispatch):
        runner = announcementrunner.get_runner()
        runner.action = mock.Mock(ref='some.thing')
        runner.runner_parameters = {
            'route': 'general'
        }
        runner.liveaction = mock.Mock(context={})

        expected_msg = 'Experimental flag is missing for action some.thing'
        self.assertRaisesRegexp(Exception, expected_msg, runner.pre_run)

    @mock.patch('st2common.models.api.trace.TraceContext.__new__')
    def test_announcement_with_trace(self, context, dispatch):
        runner = announcementrunner.get_runner()
        runner.runner_parameters = {
            'experimental': True,
            'route': 'general'
        }
        runner.liveaction = mock.Mock(context={
            'trace_context': {
                'id_': 'a',
                'trace_tag': 'b'
            }
        })

        runner.pre_run()
        (status, result, _) = runner.run({'test': 'passed'})

        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertTrue(result is not None)
        self.assertEqual(result['test'], 'passed')
        context.assert_called_once_with(TraceContext,
                                        **runner.liveaction.context['trace_context'])
        dispatch.assert_called_once_with('general', payload={'test': 'passed'},
                                         trace_context=context.return_value)
