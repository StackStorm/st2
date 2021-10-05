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

from st2common.models.db import stormbase
from st2common.constants.types import ResourceType


class TimerDB(stormbase.StormFoundationDB, stormbase.UIDFieldMixin):
    """
    Note: Right now timer is a meta model which is not persisted in the database (it's only used
    for RBAC purposes).

    Attribute:
        name: Timer name - maps to the URL path (e.g. st2/ or my/webhook/one).
    """

    RESOURCE_TYPE = ResourceType.TIMER
    UID_FIELDS = ["pack", "name"]

    name = me.StringField(required=True)
    pack = me.StringField(required=True, unique_with="name")
    type = me.StringField()
    parameters = me.DictField()

    def __init__(self, *args, **values):
        super(TimerDB, self).__init__(*args, **values)
        self.uid = self.get_uid()
