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
import os
import time

from mock import MagicMock, Mock, patch
import unittest

from oslo_config import cfg

from st2reactor.container.process_container import ProcessSensorContainer
from st2reactor.container.process_container import SENSOR_MAX_RESPAWN_COUNTS
from st2common.util import concurrency
from st2common.models.db.pack import PackDB
from st2common.persistence.pack import Pack

import st2tests.config as tests_config

MOCK_PACK_DB = PackDB(
    ref="wolfpack",
    name="wolf pack",
    description="",
    path="/opt/stackstorm/packs/wolfpack/",
)


class ProcessContainerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tests_config.parse_args()

    def test_no_sensors_dont_quit(self):
        process_container = ProcessSensorContainer(None, poll_interval=0.1)
        process_container_thread = concurrency.spawn(process_container.run)
        concurrency.sleep(0.5)
        self.assertEqual(process_container.running(), 0)
        self.assertEqual(process_container.stopped(), False)
        process_container.shutdown()
        concurrency.kill(process_container_thread)

    @patch.object(
        ProcessSensorContainer,
        "_get_sensor_id",
        MagicMock(return_value="wolfpack.StupidSensor"),
    )
    @patch.object(
        ProcessSensorContainer,
        "_dispatch_trigger_for_sensor_spawn",
        MagicMock(return_value=None),
    )
    @patch.object(Pack, "get_by_ref", MagicMock(return_value=MOCK_PACK_DB))
    @patch.object(os.path, "isdir", MagicMock(return_value=True))
    @patch("subprocess.Popen")
    @patch("st2reactor.container.process_container.create_token")
    def test_common_lib_path_in_pythonpath_env_var(
        self, mock_create_token, mock_subproc_popen
    ):
        process_mock = Mock()
        attrs = {"communicate.return_value": ("output", "error")}
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        mock_create_token = Mock()
        mock_create_token.return_value = "WHOLETTHEDOGSOUT"

        mock_dispatcher = Mock()
        process_container = ProcessSensorContainer(
            None, poll_interval=0.1, dispatcher=mock_dispatcher
        )
        sensor = {
            "class_name": "wolfpack.StupidSensor",
            "ref": "wolfpack.StupidSensor",
            "id": "567890",
            "trigger_types": ["some_trigga"],
            "pack": "wolfpack",
            "file_path": "/opt/stackstorm/packs/wolfpack/sensors/stupid_sensor.py",
            "poll_interval": 5,
        }

        process_container._enable_common_pack_libs = True
        process_container._sensors = {"pack.StupidSensor": sensor}
        process_container._spawn_sensor_process(sensor)

        _, call_kwargs = mock_subproc_popen.call_args
        actual_env = call_kwargs["env"]
        self.assertIn("PYTHONPATH", actual_env)
        pack_common_lib_path = "/opt/stackstorm/packs/wolfpack/lib"
        self.assertIn(pack_common_lib_path, actual_env["PYTHONPATH"])

    @patch.object(
        ProcessSensorContainer,
        "_get_sensor_id",
        MagicMock(return_value="wolfpack.StupidSensor"),
    )
    @patch.object(
        ProcessSensorContainer,
        "_dispatch_trigger_for_sensor_spawn",
        MagicMock(return_value=None),
    )
    @patch.object(Pack, "get_by_ref", MagicMock(return_value=MOCK_PACK_DB))
    @patch.object(os.path, "isdir", MagicMock(return_value=True))
    @patch("subprocess.Popen")
    @patch("st2reactor.container.process_container.create_token")
    def test_common_lib_path_not_in_pythonpath_env_var(
        self, mock_create_token, mock_subproc_popen
    ):
        process_mock = Mock()
        attrs = {"communicate.return_value": ("output", "error")}
        process_mock.configure_mock(**attrs)
        mock_subproc_popen.return_value = process_mock

        mock_create_token = Mock()
        mock_create_token.return_value = "WHOLETTHEDOGSOUT"

        mock_dispatcher = Mock()
        process_container = ProcessSensorContainer(
            None, poll_interval=0.1, dispatcher=mock_dispatcher
        )
        sensor = {
            "class_name": "wolfpack.StupidSensor",
            "ref": "wolfpack.StupidSensor",
            "id": "567890",
            "trigger_types": ["some_trigga"],
            "pack": "wolfpack",
            "file_path": "/opt/stackstorm/packs/wolfpack/sensors/stupid_sensor.py",
            "poll_interval": 5,
        }

        process_container._enable_common_pack_libs = False
        process_container._sensors = {"pack.StupidSensor": sensor}
        process_container._spawn_sensor_process(sensor)

        _, call_kwargs = mock_subproc_popen.call_args
        actual_env = call_kwargs["env"]
        self.assertIn("PYTHONPATH", actual_env)
        pack_common_lib_path = "/opt/stackstorm/packs/wolfpack/lib"
        self.assertNotIn(pack_common_lib_path, actual_env["PYTHONPATH"])

    @patch.object(time, "time", MagicMock(return_value=1439441533))
    def test_dispatch_triggers_on_spawn_exit(self):
        mock_dispatcher = Mock()
        process_container = ProcessSensorContainer(
            None, poll_interval=0.1, dispatcher=mock_dispatcher
        )
        sensor = {"class_name": "pack.StupidSensor"}
        process = Mock()
        process_attrs = {"pid": 1234}
        process.configure_mock(**process_attrs)
        cmd = "sensor_wrapper.py --class-name pack.StupidSensor"

        process_container._dispatch_trigger_for_sensor_spawn(sensor, process, cmd)
        mock_dispatcher.dispatch.assert_called_with(
            "core.st2.sensor.process_spawn",
            payload={
                "timestamp": 1439441533,
                "cmd": "sensor_wrapper.py --class-name pack.StupidSensor",
                "pid": 1234,
                "id": "pack.StupidSensor",
            },
        )

        process_container._dispatch_trigger_for_sensor_exit(sensor, 1)
        mock_dispatcher.dispatch.assert_called_with(
            "core.st2.sensor.process_exit",
            payload={
                "id": "pack.StupidSensor",
                "timestamp": 1439441533,
                "exit_code": 1,
            },
        )

    @patch.object(time, "time", MagicMock(return_value=1439441533))
    def test_dispatch_trigger_for_sensor_abandon(self):
        mock_dispatcher = Mock()
        process_container = ProcessSensorContainer(
            None, poll_interval=0.1, dispatcher=mock_dispatcher
        )
        sensor = {"class_name": "pack.StupidSensor"}

        process_container._dispatch_trigger_for_sensor_abandon(
            sensor, exit_code=1, respawn_count=SENSOR_MAX_RESPAWN_COUNTS
        )
        mock_dispatcher.dispatch.assert_called_with(
            "core.st2.sensor.process_abandoned",
            payload={
                "id": "pack.StupidSensor",
                "timestamp": 1439441533,
                "exit_code": 1,
                "respawn_count": SENSOR_MAX_RESPAWN_COUNTS,
            },
        )

    @patch.object(time, "time", MagicMock(return_value=1439441533))
    def test_respawn_dispatches_abandoned_after_max_respawns(self):
        mock_dispatcher = Mock()
        process_container = ProcessSensorContainer(
            None, poll_interval=0.1, dispatcher=mock_dispatcher
        )
        # Avoid touching the database for the health record update.
        process_container._update_sensor_instance = Mock()

        sensor_id = "wolfpack.StupidSensor"
        sensor = {"class_name": sensor_id, "ref": sensor_id, "pack": "wolfpack"}

        # Simulate a sensor which has already been respawned the maximum number
        # of times and just crashed again with a non-zero exit code.
        process_container._sensor_respawn_counts[sensor_id] = SENSOR_MAX_RESPAWN_COUNTS
        process_container._respawn_sensor(
            sensor_id=sensor_id, sensor=sensor, exit_code=1
        )

        mock_dispatcher.dispatch.assert_called_with(
            "core.st2.sensor.process_abandoned",
            payload={
                "id": sensor_id,
                "timestamp": 1439441533,
                "exit_code": 1,
                "respawn_count": SENSOR_MAX_RESPAWN_COUNTS,
            },
        )
        process_container._update_sensor_instance.assert_called_once()

    def test_respawn_clean_exit_does_not_dispatch_abandoned(self):
        mock_dispatcher = Mock()
        process_container = ProcessSensorContainer(
            None, poll_interval=0.1, dispatcher=mock_dispatcher
        )
        process_container._update_sensor_instance = Mock()

        sensor_id = "wolfpack.StupidSensor"
        sensor = {"class_name": sensor_id, "ref": sensor_id, "pack": "wolfpack"}

        # A clean exit (exit_code == 0) must never be treated as "abandoned".
        process_container._sensor_respawn_counts[sensor_id] = SENSOR_MAX_RESPAWN_COUNTS
        process_container._respawn_sensor(
            sensor_id=sensor_id, sensor=sensor, exit_code=0
        )

        self.assertFalse(mock_dispatcher.dispatch.called)
        self.assertFalse(process_container._update_sensor_instance.called)

    def test_respawn_settings_default_from_config(self):
        process_container = ProcessSensorContainer(None, poll_interval=0.1)
        self.assertEqual(
            process_container._max_respawn_count,
            cfg.CONF.sensorcontainer.max_respawn_count,
        )
        self.assertEqual(
            process_container._respawn_delay, cfg.CONF.sensorcontainer.respawn_delay
        )
        self.assertEqual(
            process_container._respawn_backoff_factor,
            cfg.CONF.sensorcontainer.respawn_backoff_factor,
        )

    def test_max_respawn_count_config_override(self):
        # With a higher max_respawn_count, a sensor that has been respawned the
        # old default number of times should still be respawned (not abandoned).
        cfg.CONF.set_override("max_respawn_count", 5, group="sensorcontainer")
        try:
            mock_dispatcher = Mock()
            process_container = ProcessSensorContainer(
                None, poll_interval=0.1, dispatcher=mock_dispatcher
            )
            self.assertEqual(process_container._max_respawn_count, 5)

            sensor_id = "wolfpack.StupidSensor"
            self.assertTrue(
                process_container._should_respawn_sensor(
                    sensor_id=sensor_id, sensor={}, exit_code=1
                )
            )

            # At respawn_count == 5 (the configured max) it must give up.
            process_container._sensor_respawn_counts[sensor_id] = 5
            self.assertFalse(
                process_container._should_respawn_sensor(
                    sensor_id=sensor_id, sensor={}, exit_code=1
                )
            )
        finally:
            cfg.CONF.clear_override("max_respawn_count", group="sensorcontainer")

    @patch.object(ProcessSensorContainer, "_spawn_sensor_process", MagicMock())
    @patch.object(concurrency, "sleep", MagicMock())
    def test_respawn_delay_constant_with_default_backoff(self):
        # Default backoff factor of 1 -> constant respawn_delay between attempts.
        cfg.CONF.set_override("respawn_delay", 3.0, group="sensorcontainer")
        cfg.CONF.set_override("respawn_backoff_factor", 1.0, group="sensorcontainer")
        try:
            process_container = ProcessSensorContainer(None, poll_interval=0.1)
            sensor_id = "wolfpack.StupidSensor"
            sensor = {"class_name": sensor_id, "ref": sensor_id, "pack": "wolfpack"}

            process_container._respawn_sensor(
                sensor_id=sensor_id, sensor=sensor, exit_code=1
            )
            concurrency.sleep.assert_called_with(3.0)

            # Second attempt: still constant with a backoff factor of 1.
            process_container._respawn_sensor(
                sensor_id=sensor_id, sensor=sensor, exit_code=1
            )
            concurrency.sleep.assert_called_with(3.0)
        finally:
            cfg.CONF.clear_override("respawn_delay", group="sensorcontainer")
            cfg.CONF.clear_override("respawn_backoff_factor", group="sensorcontainer")

    @patch.object(ProcessSensorContainer, "_spawn_sensor_process", MagicMock())
    @patch.object(concurrency, "sleep", MagicMock())
    def test_respawn_delay_exponential_backoff(self):
        # backoff factor of 2 -> delay grows exponentially: 2.5, 5.0, 10.0, ...
        cfg.CONF.set_override("respawn_delay", 2.5, group="sensorcontainer")
        cfg.CONF.set_override("respawn_backoff_factor", 2.0, group="sensorcontainer")
        # Raise the cap so all three attempts respawn.
        cfg.CONF.set_override("max_respawn_count", 10, group="sensorcontainer")
        try:
            process_container = ProcessSensorContainer(None, poll_interval=0.1)
            sensor_id = "wolfpack.StupidSensor"
            sensor = {"class_name": sensor_id, "ref": sensor_id, "pack": "wolfpack"}

            expected = [2.5, 5.0, 10.0]
            for expected_delay in expected:
                process_container._respawn_sensor(
                    sensor_id=sensor_id, sensor=sensor, exit_code=1
                )
                concurrency.sleep.assert_called_with(expected_delay)
        finally:
            cfg.CONF.clear_override("respawn_delay", group="sensorcontainer")
            cfg.CONF.clear_override("respawn_backoff_factor", group="sensorcontainer")
            cfg.CONF.clear_override("max_respawn_count", group="sensorcontainer")
