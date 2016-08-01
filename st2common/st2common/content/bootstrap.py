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

import os
import sys
import logging

from oslo_config import cfg

import st2common
from st2common import config
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown
from st2common.bootstrap.base import ResourceRegistrar
import st2common.bootstrap.triggersregistrar as triggers_registrar
import st2common.bootstrap.sensorsregistrar as sensors_registrar
import st2common.bootstrap.actionsregistrar as actions_registrar
import st2common.bootstrap.aliasesregistrar as aliases_registrar
import st2common.bootstrap.policiesregistrar as policies_registrar
import st2common.bootstrap.runnersregistrar as runners_registrar
import st2common.bootstrap.rulesregistrar as rules_registrar
import st2common.bootstrap.ruletypesregistrar as rule_types_registrar
import st2common.bootstrap.configsregistrar as configs_registrar
import st2common.content.utils as content_utils
from st2common.util.virtualenvs import setup_pack_virtualenv

__all__ = [
    'main'
]

LOG = logging.getLogger('st2common.content.bootstrap')

cfg.CONF.register_cli_opt(cfg.BoolOpt('experimental', default=False))


def register_opts():
    content_opts = [
        cfg.BoolOpt('all', default=False, help='Register sensors, actions and rules.'),
        cfg.BoolOpt('triggers', default=False, help='Register triggers.'),
        cfg.BoolOpt('sensors', default=False, help='Register sensors.'),
        cfg.BoolOpt('actions', default=False, help='Register actions.'),
        cfg.BoolOpt('rules', default=False, help='Register rules.'),
        cfg.BoolOpt('aliases', default=False, help='Register aliases.'),
        cfg.BoolOpt('policies', default=False, help='Register policies.'),
        cfg.BoolOpt('configs', default=False, help='Register and load pack configs.'),

        cfg.StrOpt('pack', default=None, help='Directory to the pack to register content from.'),
        cfg.BoolOpt('setup-virtualenvs', default=False, help=('Setup Python virtual environments '
                                                              'all the Python runner actions.')),

        # General options
        cfg.BoolOpt('no-fail-on-failure', default=False,
                    help=('Don\'t exit with non-zero if some resource registration fails.')),
        # Note: Fail on failure is now a default behavior. This flag is only left here for backward
        # compatibility reasons, but it's not actually used.
        cfg.BoolOpt('fail-on-failure', default=False,
                    help=('Exit with non-zero if some resource registration fails.'))
    ]
    try:
        cfg.CONF.register_cli_opts(content_opts, group='register')
    except:
        sys.stderr.write('Failed registering opts.\n')
register_opts()


def setup_virtualenvs():
    """
    Setup Python virtual environments for all the registered or the provided pack.
    """

    LOG.info('=========================================================')
    LOG.info('########### Setting up virtual environments #############')
    LOG.info('=========================================================')

    pack_dir = cfg.CONF.register.pack
    fail_on_failure = not cfg.CONF.register.no_fail_on_failure

    registrar = ResourceRegistrar()

    if pack_dir:
        pack_name = os.path.basename(pack_dir)
        pack_names = [pack_name]

        # 1. Register pack
        registrar.register_pack(pack_name=pack_name, pack_dir=pack_dir)
    else:
        # 1. Register pack
        base_dirs = content_utils.get_packs_base_paths()
        registrar.register_packs(base_dirs=base_dirs)

        # 2. Retrieve available packs (aka packs which have been registered)
        pack_names = registrar.get_registered_packs()

    setup_count = 0
    for pack_name in pack_names:
        try:
            setup_pack_virtualenv(pack_name=pack_name, update=True, logger=LOG)
        except Exception as e:
            exc_info = not fail_on_failure
            LOG.warning('Failed to setup virtualenv for pack "%s": %s', pack_name, e,
                        exc_info=exc_info)

            if fail_on_failure:
                raise e
        else:
            setup_count += 1

    LOG.info('Setup virtualenv for %s pack(s).' % (setup_count))


def register_triggers():
    pack_dir = cfg.CONF.register.pack
    fail_on_failure = not cfg.CONF.register.no_fail_on_failure

    registered_count = 0

    try:
        LOG.info('=========================================================')
        LOG.info('############## Registering triggers #####################')
        LOG.info('=========================================================')
        registered_count = triggers_registrar.register_triggers(pack_dir=pack_dir,
                                                                fail_on_failure=fail_on_failure)
    except Exception as e:
        exc_info = not fail_on_failure
        LOG.warning('Failed to register sensors: %s', e, exc_info=exc_info)

        if fail_on_failure:
            raise e

    LOG.info('Registered %s triggers.' % (registered_count))


def register_sensors():
    pack_dir = cfg.CONF.register.pack
    fail_on_failure = not cfg.CONF.register.no_fail_on_failure

    registered_count = 0

    try:
        LOG.info('=========================================================')
        LOG.info('############## Registering sensors ######################')
        LOG.info('=========================================================')
        registered_count = sensors_registrar.register_sensors(pack_dir=pack_dir,
                                                              fail_on_failure=fail_on_failure)
    except Exception as e:
        exc_info = not fail_on_failure
        LOG.warning('Failed to register sensors: %s', e, exc_info=exc_info)

        if fail_on_failure:
            raise e

    LOG.info('Registered %s sensors.' % (registered_count))


def register_actions():
    # Register runnertypes and actions. The order is important because actions require action
    # types to be present in the system.
    pack_dir = cfg.CONF.register.pack
    fail_on_failure = not cfg.CONF.register.no_fail_on_failure

    registered_count = 0

    # 1. Register runner types
    try:
        LOG.info('=========================================================')
        LOG.info('############## Registering actions ######################')
        LOG.info('=========================================================')
        runners_registrar.register_runner_types(experimental=cfg.CONF.experimental)
    except Exception as e:
        LOG.warning('Failed to register runner types: %s', e, exc_info=True)
        LOG.warning('Not registering stock runners .')
        return

    # 2. Register actions
    try:
        registered_count = actions_registrar.register_actions(pack_dir=pack_dir,
                                                              fail_on_failure=fail_on_failure)
    except Exception as e:
        exc_info = not fail_on_failure
        LOG.warning('Failed to register actions: %s', e, exc_info=exc_info)

        if fail_on_failure:
            raise e

    LOG.info('Registered %s actions.' % (registered_count))


def register_rules():
    # Register ruletypes and rules.
    pack_dir = cfg.CONF.register.pack
    fail_on_failure = not cfg.CONF.register.no_fail_on_failure

    registered_count = 0

    try:
        LOG.info('=========================================================')
        LOG.info('############## Registering rules ########################')
        LOG.info('=========================================================')
        rule_types_registrar.register_rule_types()
    except Exception as e:
        LOG.warning('Failed to register rule types: %s', e, exc_info=True)
        return

    try:
        registered_count = rules_registrar.register_rules(pack_dir=pack_dir,
                                                          fail_on_failure=fail_on_failure)
    except Exception as e:
        exc_info = not fail_on_failure
        LOG.warning('Failed to register rules: %s', e, exc_info=exc_info)

        if fail_on_failure:
            raise e

    LOG.info('Registered %s rules.', registered_count)


def register_aliases():
    pack_dir = cfg.CONF.register.pack
    fail_on_failure = not cfg.CONF.register.no_fail_on_failure

    registered_count = 0

    try:
        LOG.info('=========================================================')
        LOG.info('############## Registering aliases ######################')
        LOG.info('=========================================================')
        registered_count = aliases_registrar.register_aliases(pack_dir=pack_dir,
                                                              fail_on_failure=fail_on_failure)
    except Exception as e:
        if fail_on_failure:
            raise e

        LOG.warning('Failed to register aliases.', exc_info=True)

    LOG.info('Registered %s aliases.', registered_count)


def register_policies():
    # Register policy types and policies.
    pack_dir = cfg.CONF.register.pack
    fail_on_failure = not cfg.CONF.register.no_fail_on_failure

    registered_type_count = 0

    try:
        LOG.info('=========================================================')
        LOG.info('############## Registering policy types #################')
        LOG.info('=========================================================')
        registered_type_count = policies_registrar.register_policy_types(st2common)
    except Exception:
        LOG.warning('Failed to register policy types.', exc_info=True)

    LOG.info('Registered %s policy types.', registered_type_count)

    registered_count = 0
    try:
        LOG.info('=========================================================')
        LOG.info('############## Registering policies #####################')
        LOG.info('=========================================================')
        registered_count = policies_registrar.register_policies(pack_dir=pack_dir,
                                                                fail_on_failure=fail_on_failure)
    except Exception as e:
        exc_info = not fail_on_failure
        LOG.warning('Failed to register policies: %s', e, exc_info=exc_info)

        if fail_on_failure:
            raise e

    LOG.info('Registered %s policies.', registered_count)


def register_configs():
    pack_dir = cfg.CONF.register.pack
    fail_on_failure = not cfg.CONF.register.no_fail_on_failure

    registered_count = 0

    try:
        LOG.info('=========================================================')
        LOG.info('############## Registering configs ######################')
        LOG.info('=========================================================')
        registered_count = configs_registrar.register_configs(pack_dir=pack_dir,
                                                              fail_on_failure=fail_on_failure,
                                                              validate_configs=True)
    except Exception as e:
        exc_info = not fail_on_failure
        LOG.warning('Failed to register configs: %s', e, exc_info=exc_info)

        if fail_on_failure:
            raise e

    LOG.info('Registered %s configs.' % (registered_count))


def register_content():
    register_all = cfg.CONF.register.all

    if register_all:
        register_triggers()
        register_sensors()
        register_actions()
        register_rules()
        register_aliases()
        register_policies()
        register_configs()

    if cfg.CONF.register.triggers and not register_all:
        register_triggers()

    if cfg.CONF.register.sensors and not register_all:
        register_sensors()

    if cfg.CONF.register.actions and not register_all:
        register_actions()

    if cfg.CONF.register.rules and not register_all:
        register_rules()

    if cfg.CONF.register.aliases and not register_all:
        register_aliases()

    if cfg.CONF.register.policies and not register_all:
        register_policies()

    if cfg.CONF.register.configs and not register_all:
        register_configs()

    if cfg.CONF.register.setup_virtualenvs:
        setup_virtualenvs()


def setup(argv):
    common_setup(config=config, setup_db=True, register_mq_exchanges=True)


def teardown():
    common_teardown()


def main(argv):
    setup(argv)
    register_content()
    teardown()


# This script registers actions and rules from content-packs.
if __name__ == '__main__':
    main(sys.argv[1:])
