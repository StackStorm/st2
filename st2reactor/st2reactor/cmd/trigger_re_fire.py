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

import sys
import logging as std_logging
import pprint

from oslo_config import cfg

from st2common import config as st2cfg
from st2common import log as logging
from st2common.models.db import db_setup
from st2common.models.db import db_teardown
from st2common.persistence.trigger import TriggerInstance
from st2common.transport.reactor import TriggerDispatcher

__all__ = [
    'main'
]

CONF = cfg.CONF


def _parse_config():
    cli_opts = [
        cfg.BoolOpt('verbose',
                    short='v',
                    default=False,
                    help='Print more verbose output'),
        cfg.StrOpt('trigger-instance-id',
                   short='t',
                   required=True,
                   dest='trigger_instance_id',
                   help='Id of trigger instance'),
    ]
    CONF.register_cli_opts(cli_opts)
    st2cfg.register_opts(ignore_errors=False)

    CONF(args=sys.argv[1:])


def _setup_logging():
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s %(levelname)s %(name)s %(message)s'
            },
        },
        'handlers': {
            'console': {
                '()': std_logging.StreamHandler,
                'formatter': 'default'
            }
        },
        'root': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
    std_logging.config.dictConfig(logging_config)


def _setup_db():
    username = cfg.CONF.database.username if hasattr(cfg.CONF.database, 'username') else None
    password = cfg.CONF.database.password if hasattr(cfg.CONF.database, 'password') else None
    db_setup(cfg.CONF.database.db_name, cfg.CONF.database.host, cfg.CONF.database.port,
             username=username, password=password)


def _refire_trigger_instance(trigger_instance_id, log_):
    trigger_instance = TriggerInstance.get_by_id(trigger_instance_id)
    trigger_dispatcher = TriggerDispatcher(log_)
    trigger_dispatcher.dispatch(trigger=trigger_instance.trigger,
                                payload=trigger_instance.payload)


def main():
    _parse_config()
    if CONF.verbose:
        _setup_logging()
        output = logging.getLogger(__name__).info
    else:
        output = pprint.pprint
    _setup_db()
    _refire_trigger_instance(trigger_instance_id=CONF.trigger_instance_id,
                             log_=logging.getLogger(__name__))
    output('Trigger re-fired')
    db_teardown()
