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

import logging
import sys

import st2common.config as config

from oslo.config import cfg
from st2common.models.db import db_setup
from st2common.models.db import db_teardown


LOG = logging.getLogger('st2common.content.bootstrap')


def register_opts():
    content_opts = [
        cfg.BoolOpt('all', default=False, help='Register sensors, actions and rules.'),
        cfg.BoolOpt('sensors', default=False, help='Register sensors.'),
        cfg.BoolOpt('actions', default=False, help='Register actions.'),
        cfg.BoolOpt('rules', default=False, help='Register rules.')
    ]
    try:
        cfg.CONF.register_cli_opts(content_opts, group='register')
    except:
        sys.stderr.write('Failed registering opts.\n')
register_opts()


def register_sensors():
    try:
        LOG.info('=========================================================')
        LOG.info('############## Registering sensors ######################')
        LOG.info('=========================================================')
        # Importing here to reduce scope of dependency. This way even if st2reactor
        # is not installed bootstrap continues.
        import st2reactor.bootstrap.sensorsregistrar as sensors_registrar
        sensors_registrar.register_sensors()
    except Exception as e:
        LOG.warning('Failed to register sensors: %s', e, exc_info=True)


def register_actions():
    # Register runnertypes and actions. The order is important because actions require action
    # types to be present in the system.
    try:
        LOG.info('=========================================================')
        LOG.info('############## Registering actions ######################')
        LOG.info('=========================================================')
        # Importing here to reduce scope of dependency. This way even if st2action
        # is not installed bootstrap continues.
        import st2actions.bootstrap.runnersregistrar as runners_registrar
        runners_registrar.register_runner_types()
    except Exception as e:
        LOG.warning('Failed to register action types: %s', e, exc_info=True)
        LOG.warning('Not registering stock actions.')
    else:
        try:
            # Importing here to reduce scope of dependency. This way even if st2action
            # is not installed bootstrap continues.
            import st2actions.bootstrap.actionsregistrar as actions_registrar
            actions_registrar.register_actions()
        except Exception as e:
            LOG.warning('Failed to register actions: %s', e, exc_info=True)


def register_rules():
    # Register rules.
    try:
        LOG.info('=========================================================')
        LOG.info('############## Registering rules ######################')
        LOG.info('=========================================================')
        # Importing here to reduce scope of dependency. This way even if st2reactor
        # is not installed bootstrap continues.
        import st2reactor.bootstrap.rulesregistrar as rules_registrar
        rules_registrar.register_rules()
    except Exception as e:
        LOG.warning('Failed to register rules: %s', e, exc_info=True)


def register_content():
    if cfg.CONF.register.all:
        register_sensors()
        register_actions()
        register_rules()
        return

    if cfg.CONF.register.sensors:
        register_sensors()

    if cfg.CONF.register.actions:
        register_actions()

    if cfg.CONF.register.rules:
        register_rules()


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
