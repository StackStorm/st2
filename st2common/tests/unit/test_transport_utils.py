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
import unittest
from unittest.mock import patch

from oslo_config import cfg

from st2common.transport import utils as transport_utils


class TestTransportUtils(unittest.TestCase):
    """Test cases for transport utils module"""

    def setUp(self):
        """Reset config before each test"""
        super(TestTransportUtils, self).setUp()
        # Clear any config overrides from previous tests
        try:
            cfg.CONF.clear_override("connection_retry_max_attempts", group="messaging")
        except:
            pass
        try:
            cfg.CONF.clear_override(
                "connection_retry_interval_start", group="messaging"
            )
        except:
            pass
        try:
            cfg.CONF.clear_override("connection_retry_interval_step", group="messaging")
        except:
            pass
        try:
            cfg.CONF.clear_override("connection_retry_interval_max", group="messaging")
        except:
            pass

    @patch("st2common.transport.utils.Connection")
    def test_get_connection_includes_transport_options(self, mock_connection):
        """Test that get_connection passes transport_options with retry settings"""
        # Setup config values
        cfg.CONF.set_override("connection_retry_max_attempts", 15, group="messaging")
        cfg.CONF.set_override("connection_retry_interval_start", 2, group="messaging")
        cfg.CONF.set_override("connection_retry_interval_step", 2, group="messaging")
        cfg.CONF.set_override("connection_retry_interval_max", 60, group="messaging")

        # Call get_connection
        transport_utils.get_connection()

        # Verify Connection was called
        self.assertTrue(mock_connection.called)

        # Get the kwargs passed to Connection
        call_kwargs = mock_connection.call_args[1]

        # Verify transport_options are present
        self.assertIn("transport_options", call_kwargs)
        transport_options = call_kwargs["transport_options"]

        # Verify the retry settings
        self.assertEqual(transport_options["max_retries"], 15)
        self.assertEqual(transport_options["interval_start"], 2)
        self.assertEqual(transport_options["interval_step"], 2)
        self.assertEqual(transport_options["interval_max"], 60)

    @patch("st2common.transport.utils.Connection")
    def test_get_connection_uses_default_transport_options(self, mock_connection):
        """Test that get_connection uses default values from config"""
        # Don't override config, use defaults

        # Call get_connection
        transport_utils.get_connection()

        # Verify Connection was called
        self.assertTrue(mock_connection.called)

        # Get the kwargs passed to Connection
        call_kwargs = mock_connection.call_args[1]

        # Verify transport_options are present with defaults
        self.assertIn("transport_options", call_kwargs)
        transport_options = call_kwargs["transport_options"]

        # Verify default values (from config.py)
        self.assertEqual(transport_options["max_retries"], 10)
        self.assertEqual(transport_options["interval_start"], 1)
        self.assertEqual(transport_options["interval_step"], 1)
        self.assertEqual(transport_options["interval_max"], 30)

    @patch("st2common.transport.utils.Connection")
    def test_get_connection_with_custom_connection_kwargs(self, mock_connection):
        """Test that custom connection_kwargs don't override transport_options"""
        cfg.CONF.set_override("connection_retry_max_attempts", 5, group="messaging")

        custom_kwargs = {"heartbeat": 60, "custom_param": "value"}

        # Call get_connection with custom kwargs
        transport_utils.get_connection(connection_kwargs=custom_kwargs)

        # Verify Connection was called
        self.assertTrue(mock_connection.called)

        # Get the kwargs passed to Connection
        call_kwargs = mock_connection.call_args[1]

        # Verify transport_options are still present
        self.assertIn("transport_options", call_kwargs)
        self.assertEqual(call_kwargs["transport_options"]["max_retries"], 5)

        # Verify custom kwargs were also passed
        self.assertEqual(call_kwargs["heartbeat"], 60)
        self.assertEqual(call_kwargs["custom_param"], "value")

    @patch("st2common.transport.utils.Connection")
    def test_get_connection_zero_max_retries_for_infinite(self, mock_connection):
        """Test that setting max_retries to 0 enables infinite retries"""
        # Set max_retries to 0 for infinite retries
        cfg.CONF.set_override("connection_retry_max_attempts", 0, group="messaging")

        # Call get_connection
        transport_utils.get_connection()

        # Verify Connection was called
        self.assertTrue(mock_connection.called)

        # Get the kwargs passed to Connection
        call_kwargs = mock_connection.call_args[1]

        # Verify transport_options has max_retries set to 0
        self.assertIn("transport_options", call_kwargs)
        self.assertEqual(call_kwargs["transport_options"]["max_retries"], 0)
