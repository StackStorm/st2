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
import copy
import mongoengine as me

from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.constants.types import ResourceType
from st2common.constants.pack import PACK_VERSION_REGEX
from st2common.constants.pack import ST2_VERSION_REGEX
from st2common.util.secrets import get_secret_parameters
from st2common.util.secrets import mask_secret_parameters

__all__ = ["PackDB", "ConfigSchemaDB", "ConfigDB"]


class PackDB(stormbase.StormFoundationDB, stormbase.UIDFieldMixin, me.DynamicDocument):
    """
    System entity which represents a pack.
    """

    RESOURCE_TYPE = ResourceType.PACK
    UID_FIELDS = ["ref"]

    ref = me.StringField(required=True, unique=True)
    name = me.StringField(required=True, unique=True)
    description = me.StringField(required=True)
    keywords = me.ListField(field=me.StringField())
    version = me.StringField(regex=PACK_VERSION_REGEX, required=True)
    stackstorm_version = me.StringField(regex=ST2_VERSION_REGEX)
    python_versions = me.ListField(field=me.StringField())
    author = me.StringField(required=True)
    email = me.EmailField()
    contributors = me.ListField(field=me.StringField())
    files = me.ListField(field=me.StringField())
    path = me.StringField(required=False)
    dependencies = me.ListField(field=me.StringField())
    system = me.DictField()

    meta = {"indexes": stormbase.UIDFieldMixin.get_indexes()}

    def __init__(self, *args, **values):
        super(PackDB, self).__init__(*args, **values)
        self.uid = self.get_uid()


class ConfigSchemaDB(stormbase.StormFoundationDB):
    """
    System entity representing a config schema for a particular pack.
    """

    pack = me.StringField(
        required=True,
        unique=True,
        help_text="Name of the content pack this schema belongs to.",
    )
    attributes = stormbase.EscapedDynamicField(
        help_text="The specification for config schema attributes."
    )


class ConfigDB(stormbase.StormFoundationDB):
    """
    System entity representing pack config.
    """

    pack = me.StringField(
        required=True,
        unique=True,
        help_text="Name of the content pack this config belongs to.",
    )
    values = stormbase.EscapedDynamicField(help_text="Config values.", default={})

    def mask_secrets(self, value):
        """
        Process the model dictionary and mask secret values.

        :type value: ``dict``
        :param value: Document dictionary.

        :rtype: ``dict``
        """
        result = copy.deepcopy(value)

        config_schema = config_schema_access.get_by_pack(result["pack"])

        secret_parameters = get_secret_parameters(parameters=config_schema.attributes)
        result["values"] = mask_secret_parameters(
            parameters=result["values"], secret_parameters=secret_parameters
        )

        return result


# specialized access objects
pack_access = MongoDBAccess(PackDB)
config_schema_access = MongoDBAccess(ConfigSchemaDB)
config_access = MongoDBAccess(ConfigDB)

MODELS = [PackDB, ConfigSchemaDB, ConfigDB]
