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

from oslo_config import cfg

from st2common.models.db import db_setup
from st2common.runners.base_action import Action as BaseAction
from st2common.persistence.pack import Pack
from st2common.persistence.pack import ConfigSchema
from st2common.persistence.pack import Config
from st2common.persistence.action import Action
from st2common.persistence.action import ActionAlias
from st2common.persistence.policy import Policy
from st2common.persistence.rule import Rule
from st2common.persistence.sensor import SensorType
from st2common.persistence.trigger import Trigger
from st2common.persistence.trigger import TriggerType
from st2common.constants.pack import SYSTEM_PACK_NAMES
from st2common.services.triggers import cleanup_trigger_db_for_rule
from st2common.exceptions.db import StackStormDBObjectNotFoundError

BLOCKED_PACKS = frozenset(SYSTEM_PACK_NAMES)


class UnregisterPackAction(BaseAction):
    def __init__(self, config=None, action_service=None):
        super(UnregisterPackAction, self).__init__(
            config=config, action_service=action_service
        )
        self.initialize()

    def initialize(self):
        # 1. Setup db connection
        username = (
            cfg.CONF.database.username
            if hasattr(cfg.CONF.database, "username")
            else None
        )
        password = (
            cfg.CONF.database.password
            if hasattr(cfg.CONF.database, "password")
            else None
        )
        db_setup(
            cfg.CONF.database.db_name,
            cfg.CONF.database.host,
            cfg.CONF.database.port,
            username=username,
            password=password,
            tls=cfg.CONF.database.tls,
            tls_certificate_key_file=cfg.CONF.database.tls_certificate_key_file,
            tls_certificate_key_file_password=cfg.CONF.database.tls_certificate_key_file_password,
            tls_allow_invalid_certificates=cfg.CONF.database.tls_allow_invalid_certificates,
            tls_ca_file=cfg.CONF.database.tls_ca_file,
            ssl_cert_reqs=cfg.CONF.database.ssl_cert_reqs,  # deprecated
            authentication_mechanism=cfg.CONF.database.authentication_mechanism,
            ssl_match_hostname=cfg.CONF.database.ssl_match_hostname,
        )

    def run(self, packs):
        intersection = BLOCKED_PACKS & frozenset(packs)
        if len(intersection) > 0:
            names = ", ".join(list(intersection))
            raise ValueError(
                "Unregister includes an unregisterable pack - %s." % (names)
            )

        for pack in packs:
            self.logger.debug("Removing pack %s.", pack)
            self._unregister_sensors(pack=pack)
            self._unregister_trigger_types(pack=pack)
            self._unregister_triggers(pack=pack)
            self._unregister_actions(pack=pack)
            self._unregister_rules(pack=pack)
            self._unregister_aliases(pack=pack)
            self._unregister_policies(pack=pack)
            self._unregister_pack(pack=pack)
            self.logger.info("Removed pack %s.", pack)

    def _unregister_sensors(self, pack):
        return self._delete_pack_db_objects(pack=pack, access_cls=SensorType)

    def _unregister_trigger_types(self, pack):
        deleted_trigger_types_dbs = self._delete_pack_db_objects(
            pack=pack, access_cls=TriggerType
        )

        # 2. Check if deleted trigger is used by any other rules outside this pack
        for trigger_type_db in deleted_trigger_types_dbs:
            rule_dbs = Rule.query(
                trigger=trigger_type_db.ref, pack__ne=trigger_type_db.pack
            )

            for rule_db in rule_dbs:
                self.logger.warning(
                    'Rule "%s" references deleted trigger "%s"'
                    % (rule_db.name, trigger_type_db.ref)
                )

        return deleted_trigger_types_dbs

    def _unregister_triggers(self, pack):
        return self._delete_pack_db_objects(pack=pack, access_cls=Trigger)

    def _unregister_actions(self, pack):
        return self._delete_pack_db_objects(pack=pack, access_cls=Action)

    def _unregister_rules(self, pack):
        deleted_rules = self._delete_pack_db_objects(pack=pack, access_cls=Rule)
        for rule_db in deleted_rules:
            cleanup_trigger_db_for_rule(rule_db=rule_db)

        return deleted_rules

    def _unregister_aliases(self, pack):
        return self._delete_pack_db_objects(pack=pack, access_cls=ActionAlias)

    def _unregister_policies(self, pack):
        return self._delete_pack_db_objects(pack=pack, access_cls=Policy)

    def _unregister_pack(self, pack):
        # 1. Delete pack
        self._delete_pack_db_object(pack=pack)

        # 2. Delete corresponding config schema
        self._delete_config_schema_db_object(pack=pack)

        # 3. Delete correponding config object
        self._delete_pack_db_objects(pack=pack, access_cls=Config)

        return True

    def _delete_pack_db_object(self, pack):
        pack_db = None

        # 1. Try by ref
        try:
            pack_db = Pack.get_by_ref(value=pack)
        except StackStormDBObjectNotFoundError:
            pack_db = None

        # 2. Try by name (here for backward compatibility)
        # TODO: This shouldn't be needed in the future, remove it in v2.1 or similar
        if not pack_db:
            try:
                pack_db = Pack.get_by_name(value=pack)
            except StackStormDBObjectNotFoundError:
                pack_db = None

        if not pack_db:
            self.logger.exception("Pack DB object not found")
            return

        try:
            Pack.delete(pack_db)
        except:
            self.logger.exception("Failed to remove DB object %s.", pack_db)

    def _delete_config_schema_db_object(self, pack):
        try:
            config_schema_db = ConfigSchema.get_by_pack(value=pack)
        except StackStormDBObjectNotFoundError:
            self.logger.exception("ConfigSchemaDB object not found")
            return

        try:
            ConfigSchema.delete(config_schema_db)
        except:
            self.logger.exception("Failed to remove DB object %s.", config_schema_db)

    def _delete_pack_db_objects(self, pack, access_cls):
        db_objs = access_cls.get_all(pack=pack)

        deleted_objs = []

        for db_obj in db_objs:
            try:
                access_cls.delete(db_obj)
                deleted_objs.append(db_obj)
            except:
                self.logger.exception("Failed to remove DB object %s.", db_obj)

        return deleted_objs
