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
import mongoengine as me

from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.fields import ComplexDateTimeField
from st2common.util import date as date_utils

__all__ = ["SensorInstanceDB"]


class SensorInstanceDB(stormbase.StormFoundationDB):
    """
    Runtime health/state of a sensor as observed by the sensor container.

    This is intentionally separate from ``SensorTypeDB`` (which holds static
    registration metadata and is overwritten on every pack (re-)registration).
    A single record exists per sensor ``ref`` and is updated in place on each
    lifecycle transition (spawn / exit / abandon).

    Attribute:
        ref - Sensor reference ("<pack>.<name>"); correlation key.
        pack - Name of the content pack this sensor belongs to.
        status - Current runtime status (running, stopped, abandoned).
        hostname - Host of the sensor container which owns this sensor.
        pid - PID of the sensor process (when running).
        exit_code - Exit code of the last observed process exit.
        respawn_count - Number of respawn attempts for the current failure streak.
        updated_at - Timestamp of the last status update.
    """

    ref = me.StringField(required=True, unique=True)
    pack = me.StringField(required=True)
    status = me.StringField(
        required=True, help_text="The current runtime status of the sensor."
    )
    hostname = me.StringField(
        help_text="Host of the sensor container which owns this sensor."
    )
    pid = me.IntField(help_text="PID of the sensor process when running.")
    exit_code = me.IntField(help_text="Exit code of the last observed process exit.")
    respawn_count = me.IntField(
        default=0, help_text="Respawn attempts for the current failure streak."
    )
    updated_at = ComplexDateTimeField(
        default=date_utils.get_datetime_utc_now,
        help_text="The timestamp when the status was last updated.",
    )

    meta = {
        "indexes": [
            {"fields": ["ref"]},
            {"fields": ["status"]},
            {"fields": ["pack"]},
        ]
    }


sensor_instance_access = MongoDBAccess(SensorInstanceDB)

MODELS = [SensorInstanceDB]
