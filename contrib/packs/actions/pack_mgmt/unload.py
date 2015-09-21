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

from oslo_config import cfg

from st2common.models.db import db_setup
from st2actions.runners.pythonrunner import Action as BaseAction
from st2common.persistence.pack import Pack
from st2common.persistence.reactor import SensorType
from st2common.persistence.reactor import TriggerType
from st2common.persistence.reactor import Trigger
from st2common.persistence.reactor import Rule
from st2common.persistence.action import Action
from st2common.persistence.action import ActionAlias
from st2common.constants.pack import SYSTEM_PACK_NAMES

BLOCKED_PACKS = frozenset(SYSTEM_PACK_NAMES)


class UnregisterPackAction(BaseAction):
    def __init__(self, config=None):
        super(UnregisterPackAction, self).__init__(config=config)
        self.initialize()

    def initialize(self):
        # 1. Setup db connection
        username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
        password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
        db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
                 username=username, password=password)

    def run(self, packs):
        intersection = BLOCKED_PACKS & frozenset(packs)
        if len(intersection) > 0:
            names = ', '.join(list(intersection))
            raise ValueError('Unregister includes an unregisterable pack - %s.' % (names))

        for pack in packs:
            self.logger.debug('Removing pack %s.', pack)
            self._unregister_sensors(pack=pack)
            self._unregister_trigger_types(pack=pack)
            self._unregister_triggers(pack=pack)
            self._unregister_actions(pack=pack)
            self._unregister_rules(pack=pack)
            self._unregister_aliases(pack=pack)
            self._unregister_pack(pack=pack)
            self.logger.info('Removed pack %s.', pack)

    def _unregister_sensors(self, pack):
        return self._delete_pack_db_objects(pack=pack, access_cls=SensorType)

    def _unregister_trigger_types(self, pack):
        return self._delete_pack_db_objects(pack=pack, access_cls=TriggerType)

    def _unregister_triggers(self, pack):
        return self._delete_pack_db_objects(pack=pack, access_cls=Trigger)

    def _unregister_actions(self, pack):
        return self._delete_pack_db_objects(pack=pack, access_cls=Action)

    def _unregister_rules(self, pack):
        return self._delete_pack_db_objects(pack=pack, access_cls=Rule)

    def _unregister_aliases(self, pack):
        return self._delete_pack_db_objects(pack=pack, access_cls=ActionAlias)

    def _unregister_pack(self, pack):
        return self._delete_pack_db_object(pack=pack)

    def _delete_pack_db_object(self, pack):
        try:
            pack_db = Pack.get_by_name(value=pack)
        except ValueError:
            self.logger.exception('Pack DB object not found')
            return

        try:
            Pack.delete(pack_db)
        except:
            self.logger.exception('Failed to remove DB object %s.', pack_db)

    def _delete_pack_db_objects(self, pack, access_cls):
        db_objs = access_cls.get_all(pack=pack)

        for db_obj in db_objs:
            try:
                access_cls.delete(db_obj)
            except:
                self.logger.exception('Failed to remove DB object %s.', db_obj)
