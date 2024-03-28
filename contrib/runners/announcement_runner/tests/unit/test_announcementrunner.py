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

from __future__ import absolute_import
import mock

from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.models.api.trace import TraceContext
from st2tests.base import RunnerTestCase
import st2tests.config as tests_config
from announcement_runner import announcement_runner


mock_dispatcher = mock.Mock()


@mock.patch("st2common.transport.announcement.AnnouncementDispatcher.dispatch")
class AnnouncementRunnerTestCase(RunnerTestCase):
    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    def test_runner_creation(self, dispatch):
        runner = announcement_runner.get_runner()
        self.assertIsNotNone(runner, "Creation failed. No instance.")
        self.assertEqual(
            type(runner),
            announcement_runner.AnnouncementRunner,
            "Creation failed. No instance.",
        )
        self.assertEqual(runner._dispatcher.dispatch, dispatch)

    def test_announcement(self, dispatch):
        runner = announcement_runner.get_runner()
        runner.runner_parameters = {"experimental": True, "route": "general"}
        runner.liveaction = mock.Mock(context={})

        runner.pre_run()
        (status, result, _) = runner.run({"test": "passed"})

        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(result)
        self.assertEqual(result["test"], "passed")
        dispatch.assert_called_once_with(
            "general", payload={"test": "passed"}, trace_context=None
        )

    def test_announcement_no_experimental(self, dispatch):
        runner = announcement_runner.get_runner()
        runner.action = mock.Mock(ref="some.thing")
        runner.runner_parameters = {"route": "general"}
        runner.liveaction = mock.Mock(context={})

        expected_msg = "Experimental flag is missing for action some.thing"
        self.assertRaisesRegex(Exception, expected_msg, runner.pre_run)

    @mock.patch("st2common.models.api.trace.TraceContext.__new__")
    def test_announcement_with_trace(self, context, dispatch):
        runner = announcement_runner.get_runner()
        runner.runner_parameters = {"experimental": True, "route": "general"}
        runner.liveaction = mock.Mock(
            context={"trace_context": {"id_": "a", "trace_tag": "b"}}
        )

        runner.pre_run()
        (status, result, _) = runner.run({"test": "passed"})

        self.assertEqual(status, LIVEACTION_STATUS_SUCCEEDED)
        self.assertIsNotNone(result)
        self.assertEqual(result["test"], "passed")
        context.assert_called_once_with(
            TraceContext, **runner.liveaction.context["trace_context"]
        )
        dispatch.assert_called_once_with(
            "general", payload={"test": "passed"}, trace_context=context.return_value
        )
