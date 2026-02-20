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
from st2common.models.db.liveaction import liveaction_access
from st2common.persistence import base as persistence
from oslo_config import cfg
from st2common.util.crypto import read_crypto_key
from st2common.util.secrets import decrypt_secret_parameters, get_secret_parameters

__all__ = ["LiveAction"]


class LiveAction(persistence.StatusBasedResource):
    impl = liveaction_access
    publisher = None
    encryption_key = read_crypto_key(cfg.CONF.actionrunner.encryption_key_path)

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_publisher(cls):
        if not cls.publisher:
            cls.publisher = transport.liveaction.LiveActionPublisher()
        return cls.publisher

    @classmethod
    def delete_by_query(cls, *args, **query):
        return cls._get_impl().delete_by_query(*args, **query)

    @classmethod
    def get(self, *args, **kwargs):
        return super(LiveAction, self).get(*args, **kwargs)

    @classmethod
    def get_by_id(cls, value):
        from st2common.util import action_db

        instance = super(LiveAction, cls).get_by_id(value)
        parameters = getattr(instance, "parameters", None)
        action = getattr(instance, "action", None)
        action_parameters = action_db.get_action_parameters_specs(action_ref=action)
        secret_parameters = get_secret_parameters(parameters=action_parameters)
        decrypt_parameters = decrypt_secret_parameters(
            parameters, secret_parameters, cls.encryption_key
        )
        setattr(instance, "parameters", decrypt_parameters)
        return instance

    @classmethod
    def get_by_name(cls, value):
        # TODO: Ideally we should add decryption logic here after getting the data from mongo DB
        instance = super(LiveAction, cls).get_by_name(value)
        return instance

    @classmethod
    def get_by_uid(cls, value):
        # TODO: Ideally we should add decryption logic here after getting the data from mongo DB
        instance = super(LiveAction, cls).get_by_uid(value)
        return instance

    @classmethod
    def get_by_ref(cls, value):
        # TODO: Ideally we should add decryption logic here after getting the data from mongo DB
        instance = super(LiveAction, cls).get_by_ref(value)
        return instance

    @classmethod
    def get_by_pack(cls, value):
        # TODO: Ideally we should add decryption logic here after getting the data from mongo DB
        instance = super(LiveAction, cls).get_by_pack(value)
        return instance
