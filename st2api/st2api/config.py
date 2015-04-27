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

from oslo.config import cfg

import st2common.config as common_config
from st2common.constants.system import VERSION_STRING

CONF = cfg.CONF
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _register_common_opts():
    common_config.register_opts()


def _register_app_opts():
    # Note "host" and "port" options are registerd as part of st2common since they are also used
    # outside st2api
    api_opts = [
        cfg.ListOpt('allow_origin', default=['http://localhost:3000'],
                    help='List of origins allowed'),
        cfg.IntOpt('heartbeat', default=25,
                   help='Send empty message every N seconds to keep connection open')
    ]
    CONF.register_opts(api_opts, group='api')

    static_root = os.path.join(cfg.CONF.system.base_path, 'static')
    template_path = os.path.join(BASE_DIR, 'templates/')
    pecan_opts = [
        cfg.StrOpt('root',
                   default='st2api.controllers.root.RootController',
                   help='Action root controller'),
        cfg.StrOpt('static_root', default=static_root),
        cfg.StrOpt('template_path', default=template_path),
        cfg.ListOpt('modules', default=['st2api']),
        cfg.BoolOpt('debug', default=False),
        cfg.BoolOpt('auth_enable', default=True),
        cfg.DictOpt('errors', default={'__force_dict__': True})
    ]
    CONF.register_opts(pecan_opts, group='api_pecan')

    logging_opts = [
        cfg.StrOpt('logging', default='conf/logging.conf',
                   help='location of the logging.conf file')
    ]
    CONF.register_opts(logging_opts, group='api')


def register_opts():
    _register_common_opts()
    _register_app_opts()


def parse_args(args=None):
    CONF(args=args, version=VERSION_STRING)


register_opts()
