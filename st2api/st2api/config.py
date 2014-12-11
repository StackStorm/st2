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

from oslo.config import cfg

import st2common.config as common_config
from st2common.constants.system import VERSION_STRING

CONF = cfg.CONF


def _register_common_opts():
    common_config.register_opts()


def _register_app_opts():
    api_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='StackStorm Robotinator API server host'),
        cfg.IntOpt('port', default=9101, help='StackStorm Robotinator API server port'),
        cfg.ListOpt('allow_origin', default=['http://localhost:3000'],
                    help='List of origins allowed'),
        cfg.IntOpt('heartbeat', default=25,
                   help='Send empty message every N seconds to keep connection open')
    ]
    CONF.register_opts(api_opts, group='api')

    pecan_opts = [
        cfg.StrOpt('root',
                   default='st2api.controllers.root.RootController',
                   help='Action root controller'),
        cfg.StrOpt('static_root', default='%(confdir)s/public'),
        cfg.StrOpt('template_path',
                   default='%(confdir)s/st2api/st2api/templates'),
        cfg.ListOpt('modules', default=['st2api']),
        cfg.BoolOpt('debug', default=True),
        cfg.BoolOpt('auth_enable', default=True),
        cfg.DictOpt('errors', default={'__force_dict__': True})
    ]
    CONF.register_opts(pecan_opts, group='api_pecan')

    logging_opts = [
        cfg.StrOpt('logging', default='conf/logging.conf',
                   help='location of the logging.conf file')
    ]
    CONF.register_opts(logging_opts, group='api')


def regsiter_opts():
    _register_common_opts()
    _register_app_opts()


def parse_args(args=None):
    CONF(args=args, version=VERSION_STRING)


regsiter_opts()
