import st2common.config as config
from st2common.persistence import action
from st2common import log as logging

LOG = logging.getLogger(__name__)


class UnregisterPackAction(object):

    def run(self, packs=None):
        self._setup()
        for pack in packs:
            LOG.debug('Removing pack %s.', pack)
            self._unregister_rules(pack)
            self._unregister_triggers(pack)
            self._unregister_trigger_types(pack)
            self._unregister_actions(pack)
            LOG.info('Removed pack %s.', pack)

    @staticmethod
    def _setup():
        try:
            config.parse_args()
        except:
            pass

    @staticmethod
    def _unregister_rules(pack):
        pass

    @staticmethod
    def _unregister_triggers(pack):
        pass

    @staticmethod
    def _unregister_trigger_types(pack):
        pass

    @staticmethod
    def _unregister_actions(pack):
        action_dbs = action.Action.get_all(pack=pack)
        for action_db in action_dbs:
            try:
                action.Action.delete(action_db)
            except:
                LOG.exception('Failed to remove action %s.', action_db)
