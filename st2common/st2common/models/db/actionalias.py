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

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.constants.types import ResourceType

__all__ = ["ActionAliasDB"]


LOG = logging.getLogger(__name__)

PACK_SEPARATOR = "."


class ActionAliasDB(
    stormbase.StormFoundationDB,
    stormbase.ContentPackResourceMixin,
    stormbase.UIDFieldMixin,
):
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

    RESOURCE_TYPE = ResourceType.ACTION_ALIAS
    UID_FIELDS = ["pack", "name"]

    name = me.StringField(required=True)
    ref = me.StringField(required=True)
    description = me.StringField()
    pack = me.StringField(
        required=True, help_text="Name of the content pack.", unique_with="name"
    )
    enabled = me.BooleanField(
        required=True,
        default=True,
        help_text="A flag indicating whether the action alias is enabled.",
    )
    action_ref = me.StringField(
        required=True, help_text="Reference of the Action map this alias."
    )
    formats = me.ListField(
        help_text="Possible parameter formats that an alias supports."
    )
    ack = me.DictField(
        help_text="Parameters pertaining to the acknowledgement message."
    )
    result = me.DictField(
        help_text="Parameters pertaining to the execution result message."
    )
    extra = me.DictField(
        help_text="Additional parameters (usually adapter-specific) not covered in the schema."
    )
    immutable_parameters = me.DictField(
        help_text="Parameters to be passed to the action on every execution."
    )

    meta = {
        "indexes": [
            {"fields": ["name"]},
            {"fields": ["enabled"]},
            {"fields": ["formats"]},
        ]
        + (
            stormbase.ContentPackResourceMixin().get_indexes()
            + stormbase.UIDFieldMixin.get_indexes()
        )
    }

    def __init__(self, *args, **values):
        super(ActionAliasDB, self).__init__(*args, **values)
        self.ref = self.get_reference().ref
        self.uid = self.get_uid()

    def get_format_strings(self):
        """
        Return a list of all the supported format strings.

        :rtype: ``list`` of ``str``
        """
        result = []

        formats = getattr(self, "formats", [])
        for format_string in formats:
            if isinstance(format_string, dict) and format_string.get(
                "representation", None
            ):
                result.extend(format_string["representation"])
            else:
                result.append(format_string)

        return result


# specialized access objects
actionalias_access = MongoDBAccess(ActionAliasDB)

MODELS = [ActionAliasDB]
