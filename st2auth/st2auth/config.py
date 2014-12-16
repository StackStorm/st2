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

from oslo.config import cfg

from st2common import config as st2cfg
from st2api import config as st2apicfg
from st2common.constants.system import VERSION_STRING
from st2common.constants.auth import DEFAULT_MODE
from st2common.constants.auth import DEFAULT_BACKEND


def parse_args(args=None):
    cfg.CONF(args=args, version=VERSION_STRING)


def _register_common_opts():
    st2cfg.register_opts()


def _register_api_opts():
    st2apicfg.register_opts()


def _register_app_opts():
    auth_opts = [
        cfg.StrOpt('host', default='0.0.0.0'),
        cfg.IntOpt('port', default=9100),
        cfg.BoolOpt('secure', default=False),
        cfg.StrOpt('cert', default='/etc/apache2/ssl/mycert.crt'),
        cfg.StrOpt('key', default='/etc/apache2/ssl/mycert.key'),
        cfg.StrOpt('logging', default='conf/logging.conf'),
        cfg.BoolOpt('debug', default=False),
        cfg.StrOpt('mode', default=DEFAULT_MODE),
        cfg.StrOpt('backend', default=DEFAULT_BACKEND),
        cfg.StrOpt('backend_kwargs', default=None),
    ]
    cfg.CONF.register_cli_opts(auth_opts, group='auth')

    api_opts = [
        cfg.ListOpt('allow_origin', default=['http://localhost:3000'],
            help='List of origins allowed'),
    ]
    cfg.CONF.register_cli_opts(api_opts, group='api')


def register_opts():
    _register_common_opts()
    _register_api_opts()
    _register_app_opts()


register_opts()
