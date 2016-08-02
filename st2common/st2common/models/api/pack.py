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

import os

import jsonschema
from oslo_config import cfg

from st2common.util import schema as util_schema
from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.constants.keyvalue import USER_SCOPE
from st2common.persistence.pack import ConfigSchema
from st2common.models.api.base import BaseAPI
from st2common.models.db.pack import PackDB
from st2common.models.db.pack import ConfigSchemaDB
from st2common.models.db.pack import ConfigDB
from st2common.exceptions.db import StackStormDBObjectNotFoundError

__all__ = [
    'PackAPI',
    'ConfigSchemaAPI',
    'ConfigAPI',

    'ConfigItemSetAPI'
]


class PackAPI(BaseAPI):
    model = PackDB
    schema = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string',
                'default': None
            },
            'ref': {
                'type': 'string',
                'default': None
            },
            "uid": {
                "type": "string"
            },
            'name': {
                'type': 'string',
                'required': True
            },
            'description': {
                'type': 'string'
            },
            'keywords': {
                'type': 'array',
                'items': {'type': 'string'},
                'default': []
            },
            'version': {
                'type': 'string'
            },
            'author': {
                'type': 'string'
            },
            'email': {
                'type': 'string'
            },
            'files': {
                'type': 'array',
                'items': {'type': 'string'},
                'default': []
            }
        },
        'additionalProperties': False
    }

    @classmethod
    def to_model(cls, pack):
        name = pack.name
        description = pack.description
        ref = pack.ref
        keywords = getattr(pack, 'keywords', [])
        version = str(pack.version)
        author = pack.author
        email = pack.email
        files = getattr(pack, 'files', [])

        model = cls.model(name=name, description=description, ref=ref, keywords=keywords,
                          version=version, author=author, email=email, files=files)
        return model


class ConfigSchemaAPI(BaseAPI):
    model = ConfigSchemaDB
    schema = {
        "title": "ConfigSchema",
        "description": "Pack config schema.",
        "type": "object",
        "properties": {
            "id": {
                "description": "The unique identifier for the config schema.",
                "type": "string"
            },
            "pack": {
                "description": "The content pack this config schema belongs to.",
                "type": "string"
            },
            "attributes": {
                "description": "Config schema attributes.",
                "type": "object",
                "patternProperties": {
                    "^\w+$": util_schema.get_action_parameters_schema()
                },
                "default": {}
            }
        },
        "additionalProperties": False
    }

    @classmethod
    def to_model(cls, config_schema):
        pack = config_schema.pack
        attributes = config_schema.attributes

        model = cls.model(pack=pack, attributes=attributes)
        return model


class ConfigAPI(BaseAPI):
    model = ConfigDB
    schema = {
        "title": "Config",
        "description": "Pack config.",
        "type": "object",
        "properties": {
            "id": {
                "description": "The unique identifier for the config.",
                "type": "string"
            },
            "pack": {
                "description": "The content pack this config belongs to.",
                "type": "string"
            },
            "values": {
                "description": "Config values.",
                "type": "object",
                "default": {}
            }
        },
        "additionalProperties": False
    }

    def validate(self, validate_against_schema=False):
        # Perform base API model validation against json schema
        result = super(ConfigAPI, self).validate()

        # Perform config values validation against the config values schema
        if validate_against_schema:
            cleaned_values = self._validate_config_values_against_schema()
            result.values = cleaned_values

        return result

    def _validate_config_values_against_schema(self):
        try:
            config_schema_db = ConfigSchema.get_by_pack(value=self.pack)
        except StackStormDBObjectNotFoundError:
            # Config schema is optional
            return

        # Note: We are doing optional validation so for now, we do allow additional properties
        instance = self.values or {}
        schema = config_schema_db.attributes
        schema = util_schema.get_schema_for_resource_parameters(parameters_schema=schema,
                                                                allow_additional_properties=True)

        try:
            cleaned = util_schema.validate(instance=instance, schema=schema,
                                           cls=util_schema.CustomValidator, use_default=True,
                                           allow_default_none=True)
        except jsonschema.ValidationError as e:
            attribute = getattr(e, 'path', [])
            attribute = '.'.join(attribute)
            configs_path = os.path.join(cfg.CONF.system.base_path, 'configs/')
            config_path = os.path.join(configs_path, '%s.yaml' % (self.pack))

            msg = ('Failed validating attribute "%s" in config for pack "%s" (%s): %s' %
                   (attribute, self.pack, config_path, str(e)))
            raise jsonschema.ValidationError(msg)

        return cleaned

    @classmethod
    def to_model(cls, config):
        pack = config.pack
        values = config.values

        model = cls.model(pack=pack, values=values)
        return model


class ConfigItemSetAPI(BaseAPI):
    """
    API class used with the config set API endpoint.
    """
    model = None
    schema = {
        "title": "",
        "description": "",
        "type": "object",
        "properties": {
            "name": {
                "description": "Config item name (key)",
                "type": "string",
                "required": True
            },
            "value": {
                "description": "Config item value.",
                "type": ["string", "number", "boolean", "array", "object"],
                "required": True
            },
            "scope": {
                "description": "Config item scope (system / user)",
                "type": "string",
                "default": SYSTEM_SCOPE,
                "enum": [
                    SYSTEM_SCOPE,
                    USER_SCOPE
                ]
            },
            "user": {
                "description": "User for user-scoped items (only available to admins).",
                "type": "string",
                "required": False,
                "default": None
            }
        },
        "additionalProperties": False
    }
