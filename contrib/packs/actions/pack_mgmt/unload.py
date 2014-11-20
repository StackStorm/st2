from oslo.config import cfg

import st2common.config as config
from st2common.models.db import db_setup
from st2actions.runners.pythonrunner import Action
from st2common.persistence import action


class UnregisterPackAction(Action):

    def run(self, packs=None):
        self._setup()
        for pack in packs:
            self.logger.debug('Removing pack %s.', pack)
            self._unregister_rules(pack)
            self._unregister_triggers(pack)
            self._unregister_trigger_types(pack)
            self._unregister_actions(pack)
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

    def _unregister_rules(self, pack):
        pass

    def _unregister_triggers(self, pack):
        pass

    def _unregister_trigger_types(self, pack):
        pass

    def _unregister_actions(self, pack):
        action_dbs = action.Action.get_all(pack=pack)
        for action_db in action_dbs:
            try:
                action.Action.delete(action_db)
            except:
                self.logger.exception('Failed to remove action %s.', action_db)
