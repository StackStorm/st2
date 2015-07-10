# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mongoengine as me

from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.constants.types import ResourceType

__all__ = [
    'SensorTypeDB'
]


class SensorTypeDB(stormbase.StormBaseDB, stormbase.ContentPackResourceMixin,
                   stormbase.UIDFieldMixin):
    """
    Description of a specific type of a sensor (think of it as a sensor
    template).

    Attribute:
        pack - Name of the content pack this sensor belongs to.
        artifact_uri - URI to the artifact file.
        entry_point - Full path to the sensor entry point (e.g. module.foo.ClassSensor).
        trigger_type - A list of references to the TriggerTypeDB objects exposed by this sensor.
        poll_interval - Poll interval for this sensor.
    """

    RESOURCE_TYPE = ResourceType.SENSOR_TYPE
    UID_FIELDS = ['pack', 'name']

    name = me.StringField(required=True)
    pack = me.StringField(required=True, unique_with='name')
    artifact_uri = me.StringField()
    entry_point = me.StringField()
    trigger_types = me.ListField(field=me.StringField())
    poll_interval = me.IntField()
    enabled = me.BooleanField(default=True,
                              help_text=u'Flag indicating whether the sensor is enabled.')

    def __init__(self, *args, **values):
        super(SensorTypeDB, self).__init__(*args, **values)
        self.ref = self.get_reference().ref
        self.uid = self.get_uid()

sensor_type_access = MongoDBAccess(SensorTypeDB)

MODELS = [SensorTypeDB]
