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

from st2common.fields import ComplexDateTimeField
from st2common.models.db import stormbase
from st2common.util import date as date_utils

__all__ = ["MarkerDB", "DumperMarkerDB"]


class MarkerDB(stormbase.StormFoundationDB):
    """
    Abstract model for storing marker (or cursor) in db. This is typically used when doing
    iteration.

    :param marker: Cursor string.
    :type marker: ``str``

    :param updated_at: Timestamp when marker was updated.
    :type updated_at: ``datetime.datetime``
    """

    marker = me.StringField(required=True)
    updated_at = ComplexDateTimeField(
        default=date_utils.get_datetime_utc_now,
        help_text="The timestamp when the liveaction was created.",
    )

    meta = {"abstract": True}


class DumperMarkerDB(MarkerDB):
    """
    Marker model used by Dumper (in exporter).
    """

    pass


MODELS = [MarkerDB, DumperMarkerDB]
