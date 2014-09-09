import st2actions.bootstrap.actionsregistrar as actions_registrar
import st2actions.bootstrap.runnersregistrar as runners_registrar
from st2common import log as logging
import st2reactor.bootstrap.registrar as rules_registrar


LOG = logging.getLogger('st2common.content.bootstrap')


def register_content():
    # Register runnertypes and actions. The order is important because actions require action
    # types to be present in the system.
    try:
        runners_registrar.register_runner_types()
    except Exception as e:
        LOG.warning('Failed to register action types: %s', e, exc_info=True)
        LOG.warning('Not registering stock actions.')
    else:
        try:
            actions_registrar.register_actions()
        except Exception as e:
            LOG.warning('Failed to register actions: %s', e, exc_info=True)

    # 6. register rules
    try:
        rules_registrar.register_rules()
    except Exception as e:
        LOG.warning('Failed to register rules: %s', e, exc_info=True)


def main():
    register_content()


# This script registers actions and rules from content-packs.
if __name__ == '__main__':
    main()
