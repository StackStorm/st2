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
import six

from oslo_config import cfg
from st2common.util import isotime
from st2common.models.api.base import BaseAPI
from st2common.models.api.base import APIUIDMixin
from st2common.models.db.auth import UserDB, TokenDB, ApiKeyDB
from st2common import log as logging


LOG = logging.getLogger(__name__)


def get_system_username():
    return cfg.CONF.system_user.user


class UserAPI(BaseAPI):
    model = UserDB
    schema = {
        "title": "User",
        "type": "object",
        "properties": {"name": {"type": "string", "required": True}},
        "additionalProperties": False,
    }

    @classmethod
    def to_model(cls, user):
        name = user.name
        model = cls.model(name=name)
        return model


class TokenAPI(BaseAPI):
    model = TokenDB
    schema = {
        "title": "Token",
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "user": {"type": ["string", "null"]},
            "token": {"type": ["string", "null"]},
            "ttl": {"type": "integer", "minimum": 1},
            "expiry": {
                "type": ["string", "null"],
                "pattern": isotime.ISO8601_UTC_REGEX,
            },
            "metadata": {"type": ["object", "null"]},
        },
        "additionalProperties": False,
    }

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        doc = super(cls, cls)._from_model(model, mask_secrets=mask_secrets)
        doc["expiry"] = (
            isotime.format(model.expiry, offset=False) if model.expiry else None
        )
        return cls(**doc)

    @classmethod
    def to_model(cls, instance):
        user = str(instance.user) if instance.user else None
        token = str(instance.token) if instance.token else None
        expiry = isotime.parse(instance.expiry) if instance.expiry else None

        model = cls.model(user=user, token=token, expiry=expiry)
        return model


class ApiKeyAPI(BaseAPI, APIUIDMixin):
    model = ApiKeyDB
    schema = {
        "title": "ApiKey",
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "uid": {"type": "string"},
            "user": {"type": ["string", "null"], "default": ""},
            "key_hash": {"type": ["string", "null"]},
            "metadata": {"type": ["object", "null"]},
            "created_at": {
                "description": "The start time when the action is executed.",
                "type": "string",
                "pattern": isotime.ISO8601_UTC_REGEX,
            },
            "enabled": {
                "description": "Enable or disable the action from invocation.",
                "type": "boolean",
                "default": True,
            },
        },
        "additionalProperties": False,
    }

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        doc = super(cls, cls)._from_model(model, mask_secrets=mask_secrets)
        doc["created_at"] = (
            isotime.format(model.created_at, offset=False) if model.created_at else None
        )
        return cls(**doc)

    @classmethod
    def to_model(cls, instance):
        # If PrimaryKey ID is provided, - we want to work with existing ST2 API key
        id = getattr(instance, "id", None)
        user = str(instance.user) if instance.user else None
        key_hash = getattr(instance, "key_hash", None)
        metadata = getattr(instance, "metadata", {})
        enabled = bool(getattr(instance, "enabled", True))
        model = cls.model(
            id=id, user=user, key_hash=key_hash, metadata=metadata, enabled=enabled
        )
        return model


class ApiKeyCreateResponseAPI(BaseAPI):
    schema = {
        "title": "APIKeyCreateResponse",
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "uid": {"type": "string"},
            "user": {"type": ["string", "null"], "default": ""},
            "key": {"type": ["string", "null"]},
            "metadata": {"type": ["object", "null"]},
            "created_at": {
                "description": "The start time when the action is executed.",
                "type": "string",
                "pattern": isotime.ISO8601_UTC_REGEX,
            },
            "enabled": {
                "description": "Enable or disable the action from invocation.",
                "type": "boolean",
                "default": True,
            },
        },
        "additionalProperties": False,
    }

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        doc = cls._from_model(model=model, mask_secrets=mask_secrets)
        attrs = {attr: value for attr, value in six.iteritems(doc) if value is not None}
        attrs["created_at"] = (
            isotime.format(model.created_at, offset=False) if model.created_at else None
        )
        # key_hash is ignored.
        attrs.pop("key_hash", None)
        # key is unknown so the calling code will have to update after conversion.
        attrs["key"] = None

        return cls(**attrs)
