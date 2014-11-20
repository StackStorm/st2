from oslo.config import cfg

import st2common.config as config
from st2common.models.db import db_setup
from st2actions.runners.pythonrunner import Action
from st2common.persistence import reactor
from st2common.persistence import action


class UnregisterPackAction(Action):

    def run(self, packs=None):
        self._setup()
        for pack in packs:
            self.logger.debug('Removing pack %s.', pack)
            self._unregister_sensors(pack)
            self._unregister_trigger_types(pack)
            self._unregister_triggers(pack)
            self._unregister_actions(pack)
            self._unregister_rules(pack)
            self.logger.info('Removed pack %s.', pack)

    def _setup(self):
        # 1. Parse config
        try:
            config.parse_args()
        except:
            pass

        # 2. Setup db connection
        username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
        password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
        db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
                 username=username, password=password)

    def _unregister_sensors(self, pack):
        return self._delete_pack_db_objects(pack=pack, model_cls=reactor.SensorType)

    def _unregister_trigger_types(self, pack):
        return self._delete_pack_db_objects(pack=pack, model_cls=reactor.TriggerType)

    def _unregister_triggers(self, pack):
        return self._delete_pack_db_objects(pack=pack, model_cls=reactor.Trigger)

    def _unregister_actions(self, pack):
        return self._delete_pack_db_objects(pack=pack, model_cls=action.Action)

    def _unregister_rules(self, pack):
        pass

    def _delete_pack_db_objects(self, pack, model_cls):
        db_objs = model_cls.get_all(pack=pack)

        for db_obj in db_objs:
            try:
                model_cls.delete(db_obj)
            except:
                self.logger.exception('Failed to remove DB object %s.', db_obj)
