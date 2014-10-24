import logging
import sys

from oslo.config import cfg

import st2actions.bootstrap.actionsregistrar as actions_registrar
import st2actions.bootstrap.runnersregistrar as runners_registrar
import st2common.config as config
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
import st2reactor.bootstrap.rulesregistrar as rules_registrar


LOG = logging.getLogger('st2common.content.bootstrap')


def register_opts():
    content_opts = [
        cfg.BoolOpt('all', default=False, help='Register actions and rules.'),
        cfg.BoolOpt('actions', default=True, help='Register actions.'),
        cfg.BoolOpt('rules', default=False, help='Register rules.')
    ]
    try:
        cfg.CONF.register_cli_opts(content_opts, group='register')
    except:
        sys.stderr.write('Failed registering opts.\n')
register_opts()


def register_actions():
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


def register_rules():
    # 6. register rules
    try:
        rules_registrar.register_rules()
    except Exception as e:
        LOG.warning('Failed to register rules: %s', e, exc_info=True)


def register_content():
    if cfg.CONF.register.rules:
        register_rules()
        return

    if cfg.CONF.register.all:
        register_actions()
        register_rules()
        return

    if cfg.CONF.register.actions:
        register_actions()
        return


def _setup():
    config.parse_args()

    # 2. setup logging.
    logging.basicConfig(format='%(asctime)s %(levelname)s [-] %(message)s',
                        level=logging.DEBUG)

    # 3. all other setup which requires config to be parsed and logging to
    # be correctly setup.
    username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
    password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
             username=username, password=password)


def _teardown():
    db_teardown()


def main():
    _setup()
    register_content()
    _teardown()


# This script registers actions and rules from content-packs.
if __name__ == '__main__':
    main()
