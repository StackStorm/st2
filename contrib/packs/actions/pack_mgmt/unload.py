from st2actions.runners.pythonrunner import Action
import st2common.config as config
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
        try:
            config.parse_args()
        except:
            pass

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
