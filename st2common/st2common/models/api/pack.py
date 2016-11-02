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

from st2common import log as logging
from st2common.util import schema as util_schema
from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.constants.keyvalue import USER_SCOPE
from st2common.constants.pack import PACK_REF_WHITELIST_REGEX
from st2common.constants.pack import PACK_VERSION_REGEX
from st2common.constants.pack import ST2_VERSION_REGEX
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

    'ConfigItemSetAPI',

    'PackInstallRequestAPI',
    'PackRegisterRequestAPI',
    'PackSearchRequestAPI',
    'PackAsyncAPI'
]

LOG = logging.getLogger(__name__)


class PackAPI(BaseAPI):
    model = PackDB
    schema = {
        'type': 'object',
        'description': 'Content pack schema.',
        'properties': {
            'id': {
                'type': 'string',
                'description': 'Unique identifier for the pack.',
                'default': None
            },
            'name': {
                'type': 'string',
                'description': 'Display name of the pack. If the name only contains lowercase'
                               'letters, digits and underscores, the "ref" field is not required.',
                'required': True
            },
            'ref': {
                'type': 'string',
                'description': 'Reference for the pack, used as an internal id.',
                'default': None,
                'pattern': PACK_REF_WHITELIST_REGEX
            },
            'uid': {
                'type': 'string'
            },
            'description': {
                'type': 'string',
                'description': 'Brief description of the pack and the service it integrates with.',
                'required': True
            },
            'keywords': {
                'type': 'array',
                'description': 'Keywords describing the pack.',
                'items': {'type': 'string'},
                'default': []
            },
            'version': {
                'type': 'string',
                'description': 'Pack version. Must follow the semver format '
                               '(for instance, "0.1.0").',
                'pattern': PACK_VERSION_REGEX,
                'required': True
            },
            'author': {
                'type': 'string',
                'description': 'Pack author or authors.',
                'required': True
            },
            'email': {
                'type': 'string',
                'description': 'E-mail of the pack author.',
                'format': 'email'
            },
            'files': {
                'type': 'array',
                'description': 'A list of files inside the pack.',
                'items': {'type': 'string'},
                'default': []
            },
            'dependencies': {
                'type': 'array',
                'description': 'A list of other StackStorm packs this pack depends upon. '
                               'The same format as in "st2 pack install" is used: '
                               '"<name or full URL>[=<version or git ref>]".',
                'items': {'type': 'string'},
                'default': []
            },
            'system': {
                'type': 'object',
                'description': 'Specification for the system components and packages '
                               'required for the pack.',
                'properties': {
                    'stackstorm': {
                        'type': 'string',
                        'description': 'Required StackStorm version. Examples: ">1.6", '
                                       '">=1.8dev, <2.0"',
                        'pattern': ST2_VERSION_REGEX,
                    }
                }
            }
        }
    }

    @classmethod
    def to_model(cls, pack):
        parameters = pack.__dict__

        # Note: If some version values are not explicitly surrounded by quotes they are recognized
        # as numbers so we cast them to string
        if getattr(pack, 'version', None):
            pack.version = str(pack['version'])

        # Special case for old version which didn't follow semver format (e.g. 0.1, 1.0, etc.)
        # In case the version doesn't match that format, we simply append ".0" to the end (e.g.
        # 0.1 -> 0.1.0, 1.0, -> 1.0.0, etc.)
        dot_count = len(pack.version.split(''))
        if dot_count == 1:
            new_version = pack.version + '.0'
            LOG.info('Pack "%s" contains invalid semver version specifer, casting it to a full '
                     'semver version specifier (%s -> %s)' % (pack.name, pack.version,
                                                              new_version))
            pack.version = new_version

        parameters['keywords'] = parameters.get('keywords', [])
        parameters['files'] = parameters.get('files', [])
        parameters['dependencies'] = parameters.get('dependencies', [])
        parameters['system'] = parameters.get('system', {})

        model = cls.model(**parameters)
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
                'additionalProperties': False,
                "default": {}
            }
        },
        "additionalProperties": False
    }

    @classmethod
    def to_model(cls, config_schema):
        pack = config_schema.pack
        attributes = config_schema.attributes

         = cls.model(pack=pack, attributes=attributes)
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


class ConfigUpdateRequestAPI(BaseAPI):
    schema = {
        "type": "object"
    }


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


class PackInstallRequestAPI(BaseAPI):
    schema = {
        "type": "object",
        "properties": {
            "packs": {
                "type": "array"
            }
        }
    }


class PackRegisterRequestAPI(BaseAPI):
    schema = {
        "type": "object",
        "properties": {
            "types": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "packs": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            }
        }
    }


class PackSearchRequestAPI(BaseAPI):
    schema = {
        "type": "object",
        "oneOf": [
            {
                "properties": {
                    "query": {
                        "type": "string",
                        "required": True,
                    },
                },
                "additionalProperties": False,
            },
            {
                "properties": {
                    "pack": {
                        "type": "string",
                        "required": True,
                    },
                },
                "additionalProperties": False,
            },
        ]
    }


class PackAsyncAPI(BaseAPI):
    schema = {
        "type": "object",
        "properties": {
            "execution_id": {
                "type": "string",
                "required": True
            }
        },
        "additionalProperties": False
    }
