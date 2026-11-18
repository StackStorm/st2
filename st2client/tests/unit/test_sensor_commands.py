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

import json

import mock

from tests import base

from st2client.shell import Shell
from st2client.utils import httpclient

__all__ = ["SensorCommandTestCase"]


SENSOR_RUNNING = {
    "id": "1",
    "ref": "wolfpack.SensorA",
    "pack": "wolfpack",
    "name": "SensorA",
    "enabled": True,
    "status": "running",
    "hostname": "sensor-node-1",
    "pid": 1234,
    "exit_code": None,
    "respawn_count": 0,
    "updated_at": "2026-08-31T00:00:00.000000Z",
}

SENSOR_ABANDONED = {
    "id": "2",
    "ref": "wolfpack.SensorB",
    "pack": "wolfpack",
    "name": "SensorB",
    "enabled": True,
    "status": "abandoned",
    "hostname": "sensor-node-1",
    "pid": None,
    "exit_code": 1,
    "respawn_count": 2,
    "updated_at": "2026-08-31T00:00:00.000000Z",
}


class SensorCommandTestCase(base.BaseCLITestCase):
    def __init__(self, *args, **kwargs):
        super(SensorCommandTestCase, self).__init__(*args, **kwargs)
        self.shell = Shell()

    @mock.patch.object(
        httpclient.HTTPClient,
        "get",
        mock.MagicMock(
            return_value=base.FakeResponse(
                json.dumps([SENSOR_RUNNING, SENSOR_ABANDONED]), 200, "OK", {}
            )
        ),
    )
    def test_sensor_list_renders_status_column(self):
        return_code = self.shell.run(["sensor", "list"])
        self.assertEqual(return_code, 0)

        stdout = self.stdout.getvalue()
        # The status column header and both runtime status values are rendered.
        self.assertIn("status", stdout)
        self.assertIn("running", stdout)
        self.assertIn("abandoned", stdout)

    @mock.patch.object(
        httpclient.HTTPClient,
        "get",
        mock.MagicMock(
            return_value=base.FakeResponse(json.dumps(SENSOR_ABANDONED), 200, "OK", {})
        ),
    )
    def test_sensor_get_shows_health_fields(self):
        return_code = self.shell.run(["sensor", "get", "wolfpack.SensorB"])
        self.assertEqual(return_code, 0)

        stdout = self.stdout.getvalue()
        # get uses display_attributes = ["all"], so every health field is shown.
        for expected in [
            "status",
            "abandoned",
            "hostname",
            "exit_code",
            "respawn_count",
        ]:
            self.assertIn(expected, stdout)
