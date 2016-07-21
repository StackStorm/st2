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

from oslo_config import cfg

import st2common.config as common_config
from st2common.constants.system import VERSION_STRING

CONF = cfg.CONF


def parse_args(args=None):
    CONF(args=args, version=VERSION_STRING)


def register_opts():
    _register_common_opts()
    _register_action_runner_opts()


def _register_common_opts():
    common_config.register_opts()


def _register_action_runner_opts():
    logging_opts = [
        cfg.StrOpt('logging', default='conf/logging.conf',
                   help='location of the logging.conf file'),
    ]
    CONF.register_opts(logging_opts, group='actionrunner')

    dispatcher_pool_opts = [
        cfg.IntOpt('workflows_pool_size', default=40,
                   help='Internal pool size for dispatcher used by workflow actions.'),
        cfg.IntOpt('actions_pool_size', default=60,
                   help='Internal pool size for dispatcher used by regular actions.')
    ]
    CONF.register_opts(dispatcher_pool_opts, group='actionrunner')

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
                    help='How partial success of actions run on multiple nodes ' +
                         'should be treated.'),
        cfg.IntOpt('max_parallel_actions', default=50,
                   help='Max number of parallel remote SSH actions that should be run.  ' +
                        'Works only with Paramiko SSH runner.'),
        cfg.BoolOpt('use_ssh_config',
                    default=False,
                    help='Use the .ssh/config file. Useful to override ports etc.')
    ]
    CONF.register_opts(ssh_runner_opts, group='ssh_runner')

    cloudslang_opts = [
        cfg.StrOpt('home_dir', default='/opt/cslang',
                   help='CloudSlang home directory.'),
    ]
    CONF.register_opts(cloudslang_opts, group='cloudslang')


def get_logging_config_path():
    return CONF.actionrunner.logging


register_opts()
