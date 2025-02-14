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

from st2reactor.container.process_container import ProcessSensorContainer
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
        process_container_thread.kill()

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
