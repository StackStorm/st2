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

import os

import six
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
from st2common.util.pack import validate_config_against_schema

__all__ = [
    "PackAPI",
    "ConfigSchemaAPI",
    "ConfigAPI",
    "ConfigItemSetAPI",
    "PackInstallRequestAPI",
    "PackRegisterRequestAPI",
    "PackSearchRequestAPI",
    "PackAsyncAPI",
]

LOG = logging.getLogger(__name__)


class PackAPI(BaseAPI):
    model = PackDB
    schema = {
        "type": "object",
        "description": "Content pack schema.",
        "properties": {
            "id": {
                "type": "string",
                "description": "Unique identifier for the pack.",
                "default": None,
            },
            "name": {
                "type": "string",
                "description": "Display name of the pack. If the name only contains lowercase"
                'letters, digits and underscores, the "ref" field is not required.',
                "required": True,
            },
            "ref": {
                "type": "string",
                "description": "Reference for the pack, used as an internal id.",
                "default": None,
                "pattern": PACK_REF_WHITELIST_REGEX,
            },
            "uid": {"type": "string"},
            "description": {
                "type": "string",
                "description": "Brief description of the pack and the service it integrates with.",
                "required": True,
            },
            "keywords": {
                "type": "array",
                "description": "Keywords describing the pack.",
                "items": {"type": "string"},
                "default": [],
            },
            "version": {
                "type": "string",
                "description": "Pack version. Must follow the semver format "
                '(for instance, "0.1.0").',
                "pattern": PACK_VERSION_REGEX,
                "required": True,
            },
            "stackstorm_version": {
                "type": "string",
                "description": 'Required StackStorm version. Examples: ">1.6.0", '
                '">=1.8.0, <2.2.0"',
                "pattern": ST2_VERSION_REGEX,
            },
            "python_versions": {
                "type": "array",
                "description": (
                    "Major Python versions supported by this pack. E.g. "
                    '"2" for Python 2.7.x and "3" for Python 3.6.x'
                ),
                "items": {"type": "string", "enum": ["2", "3"]},
                "minItems": 1,
                "maxItems": 2,
                "uniqueItems": True,
                "additionalItems": True,
            },
            "author": {
                "type": "string",
                "description": "Pack author or authors.",
                "required": True,
            },
            "email": {
                "type": "string",
                "description": "E-mail of the pack author.",
                "format": "email",
            },
            "contributors": {
                "type": "array",
                "items": {"type": "string", "maxLength": 100},
                "description": (
                    "A list of people who have contributed to the pack. Format is: "
                    "Name <email address> e.g. Tomaz Muraus <tomaz@stackstorm.com>."
                ),
            },
            "files": {
                "type": "array",
                "description": "A list of files inside the pack.",
                "items": {"type": "string"},
                "default": [],
            },
            "dependencies": {
                "type": "array",
                "description": "A list of other StackStorm packs this pack depends upon. "
                'The same format as in "st2 pack install" is used: '
                '"<name or full URL>[=<version or git ref>]".',
                "items": {"type": "string"},
                "default": [],
            },
            "system": {
                "type": "object",
                "description": "Specification for the system components and packages "
                "required for the pack.",
                "default": {},
            },
            "path": {
                "type": "string",
                "description": "Location of the pack on disk in st2 system.",
                "required": False,
            },
        },
        # NOTE: We add this here explicitly so we can gracefuly add new attributs to pack.yaml
        # without breaking existing installations
        "additionalProperties": True,
    }

    def __init__(self, **values):
        # Note: If some version values are not explicitly surrounded by quotes they are recognized
        # as numbers so we cast them to string
        if values.get("version", None):
            values["version"] = str(values["version"])

        super(PackAPI, self).__init__(**values)

    def validate(self):
        # We wrap default validate() implementation and throw a more user-friendly exception in
        # case pack version doesn't follow a valid semver format and other errors
        try:
            super(PackAPI, self).validate()
        except jsonschema.ValidationError as e:
            msg = six.text_type(e)

            # Invalid version
            if "Failed validating 'pattern' in schema['properties']['version']" in msg:
                new_msg = (
                    'Pack version "%s" doesn\'t follow a valid semver format. Valid '
                    "versions and formats include: 0.1.0, 0.2.1, 1.1.0, etc."
                    % (self.version)
                )
                new_msg += "\n\n" + msg
                raise jsonschema.ValidationError(new_msg)

            # Invalid ref / name
            if "Failed validating 'pattern' in schema['properties']['ref']" in msg:
                new_msg = (
                    "Pack ref / name can only contain valid word characters (a-z, 0-9 and "
                    "_), dashes are not allowed."
                )
                new_msg += "\n\n" + msg
                raise jsonschema.ValidationError(new_msg)

            raise e

    @classmethod
    def to_model(cls, pack):
        ref = pack.ref
        name = pack.name
        description = pack.description
        keywords = getattr(pack, "keywords", [])
        version = str(pack.version)

        stackstorm_version = getattr(pack, "stackstorm_version", None)
        python_versions = getattr(pack, "python_versions", [])
        author = pack.author
        email = pack.email
        contributors = getattr(pack, "contributors", [])
        files = getattr(pack, "files", [])
        pack_dir = getattr(pack, "path", None)
        dependencies = getattr(pack, "dependencies", [])
        system = getattr(pack, "system", {})

        model = cls.model(
            ref=ref,
            name=name,
            description=description,
            keywords=keywords,
            version=version,
            author=author,
            email=email,
            contributors=contributors,
            files=files,
            dependencies=dependencies,
            system=system,
            stackstorm_version=stackstorm_version,
            path=pack_dir,
            python_versions=python_versions,
        )
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
                "type": "string",
            },
            "pack": {
                "description": "The content pack this config schema belongs to.",
                "type": "string",
            },
            "attributes": {
                "description": "Config schema attributes.",
                "type": "object",
                "patternProperties": {
                    r"^\w+$": util_schema.get_action_parameters_schema()
                },
                "additionalProperties": False,
                "default": {},
            },
        },
        "additionalProperties": False,
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
                "type": "string",
            },
            "pack": {
                "description": "The content pack this config belongs to.",
                "type": "string",
            },
            "values": {
                "description": "Config values.",
                "type": "object",
                "default": {},
            },
        },
        "additionalProperties": False,
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
        schema = config_schema_db.attributes or {}

        configs_path = os.path.join(cfg.CONF.system.base_path, "configs/")
        config_path = os.path.join(configs_path, "%s.yaml" % (self.pack))

        cleaned = validate_config_against_schema(
            config_schema=schema,
            config_object=instance,
            config_path=config_path,
            pack_name=self.pack,
        )

        return cleaned

    @classmethod
    def to_model(cls, config):
        pack = config.pack
        values = config.values

        model = cls.model(pack=pack, values=values)
        return model


class ConfigUpdateRequestAPI(BaseAPI):
    schema = {"type": "object"}


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
                "required": True,
            },
            "value": {
                "description": "Config item value.",
                "type": ["string", "number", "boolean", "array", "object"],
                "required": True,
            },
            "scope": {
                "description": "Config item scope (system / user)",
                "type": "string",
                "default": SYSTEM_SCOPE,
                "enum": [SYSTEM_SCOPE, USER_SCOPE],
            },
            "user": {
                "description": "User for user-scoped items (only available to admins).",
                "type": "string",
                "required": False,
                "default": None,
            },
        },
        "additionalProperties": False,
    }


class PackInstallRequestAPI(BaseAPI):
    schema = {
        "type": "object",
        "properties": {
            "packs": {"type": "array"},  # TODO: add enum
            "force": {
                "type": "boolean",
                "description": "Force pack installation",
                "default": False,
            },
            "skip_dependencies": {
                "type": "boolean",
                "description": "Set to True to skip pack dependency installations.",
                "default": False,
            },
            "checkout_submodules": {
                "type": "boolean",
                "description": "Checkout git submodules present in the pack.",
                "default": False,
            },
        },
    }


class PackRegisterRequestAPI(BaseAPI):
    schema = {
        "type": "object",
        "properties": {
            "types": {"type": "array", "items": {"type": "string"}},
            "packs": {"type": "array", "items": {"type": "string"}},
            "fail_on_failure": {
                "type": "boolean",
                "description": "True to fail on failure",
                "default": True,
            },
        },
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
        ],
    }


class PackAsyncAPI(BaseAPI):
    schema = {
        "type": "object",
        "properties": {"execution_id": {"type": "string", "required": True}},
        "additionalProperties": False,
    }
