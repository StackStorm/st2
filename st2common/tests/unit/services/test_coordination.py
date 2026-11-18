# Copyright 2026 The StackStorm Authors.
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

import unittest

import mock
from oslo_config import cfg

from st2common.services import coordination
import st2tests.config as tests_config


class CoordinationServiceTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super(CoordinationServiceTestCase, cls).setUpClass()
        tests_config.parse_args()

    def tearDown(self):
        cfg.CONF.clear_override(name="url", group="coordination")
        super(CoordinationServiceTestCase, self).tearDown()

    def test_get_masked_url(self):
        values = [
            (None, None),
            ("", ""),
            ("zake://", "zake://"),
            ("file:///tmp", "file:///tmp"),
            ("redis://127.0.0.1:6379", "redis://127.0.0.1:6379"),
            ("redis://user@127.0.0.1:6379", "redis://user@127.0.0.1:6379"),
            ("redis://user:secret@127.0.0.1:6379", "redis://user:**@127.0.0.1:6379"),
            ("redis://:secret@127.0.0.1:6379", "redis://:**@127.0.0.1:6379"),
            (
                "redis://127.0.0.1:26379?sentinel=mymaster&password=secret",
                "redis://127.0.0.1:26379?sentinel=mymaster&password=**",
            ),
            (
                "redis://127.0.0.1:26379?sentinel_password=secret&timeout=5",
                "redis://127.0.0.1:26379?sentinel_password=**&timeout=5",
            ),
            (
                "mysql://st2:secret@127.0.0.1:3306/st2",
                "mysql://st2:**@127.0.0.1:3306/st2",
            ),
        ]

        for url, expected in values:
            self.assertEqual(coordination.get_masked_url(url), expected)
            if url:
                self.assertNotIn("secret", coordination.get_masked_url(url))

    @mock.patch.object(coordination, "LOG")
    @mock.patch.object(coordination.coordination, "get_coordinator")
    def test_coordinator_setup_logs_successful_connection(
        self, mock_get_coordinator, mock_log
    ):
        cfg.CONF.set_override(
            name="url",
            override="redis://user:secret@127.0.0.1:6379",
            group="coordination",
        )

        coordinator = coordination.coordinator_setup(start_heart=False)

        self.assertEqual(coordinator, mock_get_coordinator.return_value)
        coordinator.start.assert_called_once_with(start_heart=False)

        info_messages = [call[0][0] for call in mock_log.info.call_args_list]
        self.assertEqual(
            info_messages,
            [
                'Connecting to coordination backend "redis://user:**@127.0.0.1:6379".',
                'Successfully connected to coordination backend "redis://user:**@'
                '127.0.0.1:6379".',
            ],
        )

    @mock.patch.object(coordination, "LOG")
    @mock.patch.object(coordination.coordination, "get_coordinator")
    def test_coordinator_setup_connection_failure_not_logged_as_success(
        self, mock_get_coordinator, mock_log
    ):
        cfg.CONF.set_override(
            name="url", override="redis://127.0.0.1:6379", group="coordination"
        )
        mock_get_coordinator.return_value.start.side_effect = Exception(
            "Connection refused"
        )

        self.assertRaisesRegex(
            Exception,
            "Connection refused",
            coordination.coordinator_setup,
            start_heart=False,
        )

        info_messages = [call[0][0] for call in mock_log.info.call_args_list]
        self.assertEqual(
            info_messages,
            ['Connecting to coordination backend "redis://127.0.0.1:6379".'],
        )

    @mock.patch.object(coordination, "LOG")
    def test_coordinator_setup_noop_driver_no_connection_log(self, mock_log):
        cfg.CONF.set_override(name="url", override=None, group="coordination")

        coordinator = coordination.coordinator_setup(start_heart=False)

        self.assertIsInstance(coordinator, coordination.NoOpDriver)
        mock_log.info.assert_not_called()
