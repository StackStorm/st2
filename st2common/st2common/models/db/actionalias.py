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

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.constants.types import ResourceType

__all__ = [
    'ActionAliasDB'
]


LOG = logging.getLogger(__name__)

PACK_SEPARATOR = '.'


class ActionAliasDB(stormbase.StormBaseDB, stormbase.ContentPackResourceMixin,
                    stormbase.UIDFieldMixin):
    """
    Database entity that represent an Alias for an action.

    Attribute:
        pack: Pack to which this alias belongs to.
        name: Alias name.
        ref: Alias reference (pack + name).
        enabled: A flag indicating whether this alias is enabled in the system.
        action_ref: Reference of an action this alias belongs to.
        formats: Alias format strings.
    """

    RESOURCE_TYPE = ResourceType.ACTION
    UID_FIELDS = ['pack', 'name']

    ref = me.StringField(required=True)
    pack = me.StringField(
        required=True,
        help_text='Name of the content pack.')
    enabled = me.BooleanField(
        required=True, default=True,
        help_text='A flag indicating whether the action alias is enabled.')
    action_ref = me.StringField(
        required=True,
        help_text='Reference of the Action map this alias.')
    formats = me.ListField(
        field=me.StringField(),
        help_text='Possible parameter formats that an alias supports.')
    aliases = me.ListField(
        field=me.StringField(),
        help_text='Parameter formats hidden from a public list.')
    ack = me.DictField(
        help_text='Parameters pertaining to the acknowledgement message.'
    )
    result = me.DictField(
        help_text='Parameters pertaining to the execution result message.'
    )

    meta = {
        'indexes': ['name']
    }

    def __init__(self, *args, **values):
        super(ActionAliasDB, self).__init__(*args, **values)
        self.ref = self.get_reference().ref
        self.uid = self.get_uid()


# specialized access objects
actionalias_access = MongoDBAccess(ActionAliasDB)

MODELS = [ActionAliasDB]
