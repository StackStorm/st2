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

from st2common.models.db import stormbase
from st2common.constants.types import ResourceType


class WebhookDB(stormbase.StormFoundationDB, stormbase.UIDFieldMixin):
    """
    Note: Right now webhook is a meta model which is not persisted in the database.

    Attribute:
        name: Webhook name - maps to the URL path (e.g. st2/ or my/webhook/one).
    """

    RESOURCE_TYPE = ResourceType.WEBHOOK
    UID_FIELDS = ['name']

    name = me.StringField(required=True)

    def __init__(self, *args, **values):
        super(WebhookDB, self).__init__(*args, **values)
        self.uid = self.get_uid()
