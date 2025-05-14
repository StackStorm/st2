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
import unittest

from oslo_config import cfg

# This import must be early for import-time side-effects.
import st2tests.config as tests_config

from st2reactor.garbage_collector import base as garbage_collector


class GarbageCollectorServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tests_config.parse_args()

    def tearDown(self):
        # Reset gc_max_idle_sec with a value of 1 to reenable for other tests.
        cfg.CONF.set_override("gc_max_idle_sec", 1, group="workflow_engine")
        super(GarbageCollectorServiceTest, self).tearDown()

    @mock.patch.object(
        garbage_collector.GarbageCollectorService,
        "_purge_action_executions",
        mock.MagicMock(return_value=None),
    )
    @mock.patch.object(
        garbage_collector.GarbageCollectorService,
        "_purge_action_executions_output",
        mock.MagicMock(return_value=None),
    )
    @mock.patch.object(
        garbage_collector.GarbageCollectorService,
        "_purge_trigger_instances",
        mock.MagicMock(return_value=None),
    )
    @mock.patch.object(
        garbage_collector.GarbageCollectorService,
        "_timeout_inquiries",
        mock.MagicMock(return_value=None),
    )
    @mock.patch.object(
        garbage_collector.GarbageCollectorService,
        "_purge_orphaned_workflow_executions",
        mock.MagicMock(return_value=None),
    )
    def test_orphaned_workflow_executions_gc_enabled(self):
        # Mock the default value of gc_max_idle_sec with a value >= 1 to enable. The config
        # gc_max_idle_sec is assigned to _workflow_execution_max_idle which gc checks to see
        # whether to run the routine.
        cfg.CONF.set_override("gc_max_idle_sec", 1, group="workflow_engine")

        # Run the garbage collection.
        gc = garbage_collector.GarbageCollectorService(sleep_delay=0)
        gc._perform_garbage_collection()

        # Make sure _purge_orphaned_workflow_executions is called.
        self.assertTrue(
            garbage_collector.GarbageCollectorService._purge_orphaned_workflow_executions.called
        )

    @mock.patch.object(
        garbage_collector.GarbageCollectorService,
        "_purge_action_executions",
        mock.MagicMock(return_value=None),
    )
    @mock.patch.object(
        garbage_collector.GarbageCollectorService,
        "_purge_action_executions_output",
        mock.MagicMock(return_value=None),
    )
    @mock.patch.object(
        garbage_collector.GarbageCollectorService,
        "_purge_trigger_instances",
        mock.MagicMock(return_value=None),
    )
    @mock.patch.object(
        garbage_collector.GarbageCollectorService,
        "_timeout_inquiries",
        mock.MagicMock(return_value=None),
    )
    @mock.patch.object(
        garbage_collector.GarbageCollectorService,
        "_purge_orphaned_workflow_executions",
        mock.MagicMock(return_value=None),
    )
    def test_orphaned_workflow_executions_gc_disabled(self):
        # Mock the default value of gc_max_idle_sec with a value of 0 to disable. The config
        # gc_max_idle_sec is assigned to _workflow_execution_max_idle which gc checks to see
        # whether to run the routine.
        cfg.CONF.set_override("gc_max_idle_sec", 0, group="workflow_engine")

        # Run the garbage collection.
        gc = garbage_collector.GarbageCollectorService(sleep_delay=0)
        gc._perform_garbage_collection()

        # Make sure _purge_orphaned_workflow_executions is not called.
        self.assertFalse(
            garbage_collector.GarbageCollectorService._purge_orphaned_workflow_executions.called
        )
