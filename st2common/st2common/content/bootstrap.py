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

from st2common import config
from st2common.script_setup import setup as common_setup
from st2common.script_setup import teardown as common_teardown
from st2common.bootstrap.base import ResourceRegistrar
import st2common.content.utils as content_utils
from st2client.client import Client
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
        cfg.BoolOpt('runners', default=False, help='Register runners.'),
        cfg.BoolOpt('rules', default=False, help='Register rules.'),
        cfg.BoolOpt('aliases', default=False, help='Register aliases.'),
        cfg.BoolOpt('policies', default=False, help='Register policies.'),
        cfg.BoolOpt('configs', default=False, help='Register and load pack configs.'),

        cfg.StrOpt('pack', default=None, help='Directory to the pack to register content from.'),
        cfg.StrOpt('runner-dir', default=None, help='Directory to load runners from.'),
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

    opts = [
        cfg.StrOpt('api-url', default=None,
                   help='Base URL to the API endpoint excluding the version.'),
        cfg.StrOpt('token', default=None,
                   help='Access token for user authentication.')
    ]

    try:
        cfg.CONF.register_cli_opts(content_opts, group='register')
        cfg.CONF.register_cli_opts(opts)
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


def print_registered(registered):
    for name in registered:
        LOG.info('===========================%s=======================', '=' * len(name))
        LOG.info('############## Registering %s ######################', name)
        LOG.info('===========================%s=======================', '=' * len(name))
        LOG.info('Registered %s %s.' % (registered[name], name))


def register_content():
    register_all = cfg.CONF.register.all

    types = None

    if not register_all:
        types = []

        if cfg.CONF.register.triggers:
            types.append('trigger')

        if cfg.CONF.register.sensors:
            types.append('sensor')

        if cfg.CONF.register.runners:
            types.append('runner')

        if cfg.CONF.register.actions:
            types.append('action')

        if cfg.CONF.register.rules:
            types.append('rule')

        if cfg.CONF.register.aliases:
            types.append('alias')

        if cfg.CONF.register.policies:
            types.append('policy')

        if cfg.CONF.register.configs:
            types.append('config')

    api_url = cfg.CONF.api_url
    token = cfg.CONF.token

    client = Client(api_url=api_url, token=token)

    result = client.packs.register(types)

    print_registered(result)

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
