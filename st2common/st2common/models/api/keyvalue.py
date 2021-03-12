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
import copy
import datetime

from oslo_config import cfg
import six

from st2common.constants.keyvalue import (
    FULL_SYSTEM_SCOPE,
    FULL_USER_SCOPE,
    ALLOWED_SCOPES,
)
from st2common.constants.keyvalue import SYSTEM_SCOPE, USER_SCOPE
from st2common.exceptions.keyvalue import (
    CryptoKeyNotSetupException,
    InvalidScopeException,
)
from st2common.log import logging
from st2common.util import isotime
from st2common.util import date as date_utils
from st2common.util.crypto import read_crypto_key, symmetric_encrypt, symmetric_decrypt
from st2common.models.api.base import BaseAPI
from st2common.models.system.keyvalue import UserKeyReference
from st2common.models.db.keyvalue import KeyValuePairDB

__all__ = ["KeyValuePairAPI", "KeyValuePairSetAPI"]

LOG = logging.getLogger(__name__)


class KeyValuePairAPI(BaseAPI):
    crypto_setup = False
    model = KeyValuePairDB
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "uid": {"type": "string"},
            "name": {"type": "string"},
            "description": {"type": "string"},
            "value": {"type": "string", "required": True},
            "secret": {"type": "boolean", "required": False, "default": False},
            "encrypted": {"type": "boolean", "required": False, "default": False},
            "scope": {
                "type": "string",
                "required": False,
                "default": FULL_SYSTEM_SCOPE,
            },
            "expire_timestamp": {
                "type": "string",
                "pattern": isotime.ISO8601_UTC_REGEX,
            },
            # Note: Those values are only used for input
            # TODO: Improve
            "ttl": {"type": "integer"},
        },
        "additionalProperties": False,
    }

    @staticmethod
    def _setup_crypto():
        if KeyValuePairAPI.crypto_setup:
            # Crypto already set up
            return

        LOG.info("Checking if encryption is enabled for key-value store.")
        KeyValuePairAPI.is_encryption_enabled = cfg.CONF.keyvalue.enable_encryption
        LOG.debug("Encryption enabled? : %s", KeyValuePairAPI.is_encryption_enabled)
        if KeyValuePairAPI.is_encryption_enabled:
            KeyValuePairAPI.crypto_key_path = cfg.CONF.keyvalue.encryption_key_path
            LOG.info(
                "Encryption enabled. Looking for key in path %s",
                KeyValuePairAPI.crypto_key_path,
            )
            if not os.path.exists(KeyValuePairAPI.crypto_key_path):
                msg = (
                    "Encryption key file does not exist in path %s."
                    % KeyValuePairAPI.crypto_key_path
                )
                LOG.exception(msg)
                LOG.info(
                    "All API requests will now send out BAD_REQUEST "
                    + "if you ask to store secrets in key value store."
                )
                KeyValuePairAPI.crypto_key = None
            else:
                KeyValuePairAPI.crypto_key = read_crypto_key(
                    key_path=KeyValuePairAPI.crypto_key_path
                )
        KeyValuePairAPI.crypto_setup = True

    @classmethod
    def from_model(cls, model, mask_secrets=True):
        if not KeyValuePairAPI.crypto_setup:
            KeyValuePairAPI._setup_crypto()

        doc = cls._from_model(model, mask_secrets=mask_secrets)

        if getattr(model, "expire_timestamp", None) and model.expire_timestamp:
            doc["expire_timestamp"] = isotime.format(
                model.expire_timestamp, offset=False
            )

        encrypted = False
        secret = getattr(model, "secret", False)
        if secret:
            encrypted = True

        if not mask_secrets and secret:
            doc["value"] = symmetric_decrypt(KeyValuePairAPI.crypto_key, model.value)
            encrypted = False

        scope = getattr(model, "scope", SYSTEM_SCOPE)
        if scope:
            doc["scope"] = scope

        key = doc.get("name", None)
        if (scope == USER_SCOPE or scope == FULL_USER_SCOPE) and key:
            doc["user"] = UserKeyReference.get_user(key)
            doc["name"] = UserKeyReference.get_name(key)

        doc["encrypted"] = encrypted
        attrs = {attr: value for attr, value in six.iteritems(doc) if value is not None}
        return cls(**attrs)

    @classmethod
    def to_model(cls, kvp):
        if not KeyValuePairAPI.crypto_setup:
            KeyValuePairAPI._setup_crypto()

        kvp_id = getattr(kvp, "id", None)
        name = getattr(kvp, "name", None)
        description = getattr(kvp, "description", None)
        value = kvp.value
        original_value = value
        secret = False

        if getattr(kvp, "ttl", None):
            expire_timestamp = date_utils.get_datetime_utc_now() + datetime.timedelta(
                seconds=kvp.ttl
            )
        else:
            expire_timestamp = None

        encrypted = getattr(kvp, "encrypted", False)
        secret = getattr(kvp, "secret", False)

        # If user transmitted the value in an pre-encrypted format, we perform the decryption here
        # to ensure data integrity. Besides that, we store data as-is.
        # Keep in mind that encrypted=True also always implies secret=True. If we didn't do
        # that and supported encrypted=True, secret=False, this would allow users to decrypt
        # any encrypted value.
        if encrypted:
            secret = True

            cls._verif_key_is_set_up(name=name)

            try:
                symmetric_decrypt(KeyValuePairAPI.crypto_key, value)
            except Exception:
                msg = (
                    'Failed to verify the integrity of the provided value for key "%s". Ensure '
                    "that the value is encrypted with the correct key and not corrupted."
                    % (name)
                )
                raise ValueError(msg)

            # Additional safety check to ensure that the value hasn't been decrypted
            if value != original_value:
                raise ValueError(
                    f"The encrypted value {value} is not the"
                    f" same original encrypted value {original_value}."
                )
        elif secret:
            cls._verif_key_is_set_up(name=name)

            value = symmetric_encrypt(KeyValuePairAPI.crypto_key, value)

        scope = getattr(kvp, "scope", FULL_SYSTEM_SCOPE)

        if scope not in ALLOWED_SCOPES:
            raise InvalidScopeException(
                'Invalid scope "%s"! Allowed scopes are %s.' % (scope, ALLOWED_SCOPES)
            )

        # NOTE: For security reasons, encrypted always implies secret=True. See comment
        # above for explanation.
        if encrypted and not secret:
            raise ValueError(
                "encrypted option can only be used in combination with secret " "option"
            )

        model = cls.model(
            id=kvp_id,
            name=name,
            description=description,
            value=value,
            secret=secret,
            scope=scope,
            expire_timestamp=expire_timestamp,
        )

        return model

    @classmethod
    def _verif_key_is_set_up(cls, name):
        if not KeyValuePairAPI.crypto_key:
            msg = (
                "Crypto key not found in %s. Unable to encrypt / decrypt value for key %s."
                % (KeyValuePairAPI.crypto_key_path, name)
            )
            raise CryptoKeyNotSetupException(msg)


class KeyValuePairSetAPI(KeyValuePairAPI):
    """
    API model for key value set operations.
    """

    schema = copy.deepcopy(KeyValuePairAPI.schema)
    schema["properties"]["ttl"] = {"description": "Items TTL", "type": "integer"}
    schema["properties"]["user"] = {
        "description": (
            "User to which the value should be scoped to. Only applicable to "
            "scope == user"
        ),
        "type": "string",
        "default": None,
    }
