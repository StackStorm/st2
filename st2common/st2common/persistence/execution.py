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
from st2common import transport
from st2common.models.db import MongoDBAccess
from st2common.models.db.execution import ActionExecutionDB
from st2common.models.db.execution import ActionExecutionOutputDB
from st2common.persistence.base import Access
from oslo_config import cfg
from st2common.util.crypto import read_crypto_key
from st2common.util.secrets import get_secret_parameters
from st2common.util.secrets import decrypt_secret_parameters

__all__ = [
    "ActionExecution",
    "ActionExecutionOutput",
]


class ActionExecution(Access):
    impl = MongoDBAccess(ActionExecutionDB)
    publisher = None
    encryption_key = read_crypto_key(cfg.CONF.actionrunner.encryption_key_path)

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_publisher(cls):
        if not cls.publisher:
            cls.publisher = transport.execution.ActionExecutionPublisher()
        return cls.publisher

    @classmethod
    def delete_by_query(cls, *args, **query):
        return cls._get_impl().delete_by_query(*args, **query)

    @classmethod
    def get_by_name(cls, value):
        result = cls.get(name=value, raise_exception=True)
        return result

    @classmethod
    def get_by_id(cls, value):
        instance = super(ActionExecution, cls).get_by_id(value)
        instance = cls._decrypt_secrets(instance)
        return instance

    @classmethod
    def get_by_uid(cls, value):
        result = cls.get(uid=value, raise_exception=True)
        return result

    @classmethod
    def get_by_ref(cls, value):
        result = cls.get(ref=value, raise_exception=True)
        return result

    @classmethod
    def get_by_pack(cls, value):
        result = cls.get(pack=value, raise_exception=True)
        return result

    @classmethod
    def get(cls, *args, **kwargs):
        instance = super(ActionExecution, cls).get(*args, **kwargs)
        if instance is None:
            return instance
        # Decrypt secrets if any
        instance = cls._decrypt_secrets(instance)
        return instance

    @classmethod
    def _decrypt_secrets(cls, instance):
        if instance is None:
            return instance
        action = getattr(instance, "action", {})
        runner = getattr(instance, "runner", {})
        parameters = {}
        parameters.update(action.get("parameters", {}))
        parameters.update(runner.get("runner_parameters", {}))
        secret_parameters = get_secret_parameters(parameters=parameters)

        decrypt_parameters = decrypt_secret_parameters(
            getattr(instance, "parameters", {}), secret_parameters, cls.encryption_key
        )
        setattr(instance, "parameters", decrypt_parameters)

        liveaction_parameter = getattr(instance, "liveaction", {}).get("parameters", {})
        if liveaction_parameter:
            decrypt_liveaction_parameters = decrypt_secret_parameters(
                liveaction_parameter, secret_parameters, cls.encryption_key
            )
            instance.liveaction["parameters"] = decrypt_liveaction_parameters

        return instance


class ActionExecutionOutput(Access):
    impl = MongoDBAccess(ActionExecutionOutputDB)

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_publisher(cls):
        if not cls.publisher:
            cls.publisher = transport.execution.ActionExecutionOutputPublisher()
        return cls.publisher

    @classmethod
    def delete_by_query(cls, *args, **query):
        return cls._get_impl().delete_by_query(*args, **query)
