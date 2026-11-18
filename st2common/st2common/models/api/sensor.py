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
from st2common.models.api.base import BaseAPI
from st2common.models.api.trigger import TriggerTypeAPI
from st2common.models.db.sensor import SensorTypeDB
from st2common.models.utils import sensor_type_utils


class SensorTypeAPI(BaseAPI):
    model = SensorTypeDB
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string", "default": None},
            "ref": {"type": "string"},
            "uid": {"type": "string"},
            "class_name": {"type": "string", "required": True},
            "pack": {"type": "string"},
            "description": {"type": "string"},
            "artifact_uri": {
                "type": "string",
            },
            "entry_point": {
                "type": "string",
            },
            "enabled": {
                "description": "Enable or disable the sensor.",
                "type": "boolean",
                "default": True,
            },
            "trigger_types": {
                "type": "array",
                "items": TriggerTypeAPI.schema,
                "default": [],
            },
            "poll_interval": {"type": "number"},
            "metadata_file": {
                "description": "Path to the metadata file relative to the pack directory.",
                "type": "string",
                "default": "",
            },
            # Runtime health fields. These are read-only and are merged in from
            # the separate SensorInstanceDB collection by the API controller;
            # they are not part of to_model() and are never persisted back onto
            # SensorTypeDB.
            "status": {
                "description": "Current runtime status of the sensor "
                "(running, stopped, abandoned). Null if the sensor has never run.",
                "type": ["string", "null"],
            },
            "hostname": {
                "description": "Host of the sensor container which owns this sensor.",
                "type": ["string", "null"],
            },
            "pid": {
                "description": "PID of the sensor process when running.",
                "type": ["integer", "null"],
            },
            "exit_code": {
                "description": "Exit code of the last observed process exit.",
                "type": ["integer", "null"],
            },
            "respawn_count": {
                "description": "Respawn attempts for the current failure streak.",
                "type": ["integer", "null"],
            },
            "updated_at": {
                "description": "Timestamp when the runtime status was last updated.",
                "type": ["string", "null"],
            },
        },
        "additionalProperties": False,
    }

    @classmethod
    def to_model(cls, sensor_type):
        model = sensor_type_utils.to_sensor_db_model(sensor_api_model=sensor_type)
        return model
