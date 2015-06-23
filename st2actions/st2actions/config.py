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

"""
Configuration options registration and useful routines.
"""

import sys

from oslo.config import cfg

import st2common.config as common_config
from st2common.constants.system import VERSION_STRING
common_config.register_opts()

CONF = cfg.CONF

logging_opts = [
    cfg.StrOpt('logging', default='conf/logging.conf',
               help='location of the logging.conf file'),
    cfg.StrOpt('python_binary', default=sys.executable,
               help='Python binary which will be used by Python actions.')
]
CONF.register_opts(logging_opts, group='actionrunner')

db_opts = [
    cfg.StrOpt('host', default='0.0.0.0', help='host of db server'),
    cfg.IntOpt('port', default=27017, help='port of db server'),
    cfg.StrOpt('db_name', default='st2', help='name of database')
]
CONF.register_opts(db_opts, group='database')

ssh_runner_opts = [
    cfg.StrOpt('remote_dir',
               default='/tmp',
               help='Location of the script on the remote filesystem.'),
    cfg.BoolOpt('allow_partial_failure',
                default=False,
                help='How partial success of actions run on multiple nodes should be treated.')
]
CONF.register_opts(ssh_runner_opts, group='ssh_runner')

mistral_opts = [
    cfg.StrOpt('v2_base_url', default='http://localhost:8989/v2',
               help='Mistral v2 API server root endpoint.'),
    cfg.IntOpt('max_attempts', default=180,
               help='Maximum no of attempts made to connect to Mistral.'),
    cfg.IntOpt('retry_wait', default=5,
               help='Time in seconds to wait before retrying connection to Mistral.')
]
CONF.register_opts(mistral_opts, group='mistral')

cloudslang_opts = [
    cfg.StrOpt('home_dir', default='/opt/cslang',
               help='CloudSlang home directory.'),
]
CONF.register_opts(cloudslang_opts, group='cloudslang')

scheduler_opts = [
    cfg.IntOpt('delayed_execution_recovery', default=600,
               help='The time in seconds to wait before recovering delayed action executions.'),
    cfg.IntOpt('rescheduling_interval', default=300,
               help='The frequency for rescheduling action executions.')
]
CONF.register_opts(scheduler_opts, group='scheduler')


def parse_args(args=None):
    CONF(args=args, version=VERSION_STRING)


def get_logging_config_path():
    return CONF.actionrunner.logging
