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

import os

from oslo_config import cfg

import st2common.config as common_config
from st2common.constants.system import VERSION_STRING

CONF = cfg.CONF
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def parse_args(args=None):
    CONF(args=args, version=VERSION_STRING)


def register_opts():
    _register_common_opts()
    _register_app_opts()


def _register_common_opts():
    common_config.register_opts()


def get_logging_config_path():
    return cfg.CONF.stream.logging


def _register_app_opts():
    # Note "allow_origin", "mask_secrets" options are registered as part of st2common config since
    # they are also used outside st2stream
    api_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='StackStorm stream API server host'),
        cfg.IntOpt('port', default=9102, help='StackStorm API stream, server port'),
        cfg.IntOpt('heartbeat', default=25,
                   help='Send empty message every N seconds to keep connection open'),
        cfg.BoolOpt('debug', default=False,
                    help='Specify to enable debug mode.'),
        cfg.StrOpt('logging', default='conf/logging.conf',
                   help='location of the logging.conf file')
    ]
    CONF.register_opts(api_opts, group='stream')
