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

from oslo_config import cfg

from st2common import config as st2cfg
from st2common.constants.system import VERSION_STRING
from st2common.constants.auth import DEFAULT_MODE
from st2common.constants.auth import DEFAULT_BACKEND
from st2common.constants.auth import VALID_MODES
from st2auth.backends import get_available_backends


def parse_args(args=None):
    cfg.CONF(args=args, version=VERSION_STRING)


def register_opts():
    _register_common_opts()
    _register_app_opts()


def get_logging_config_path():
    return cfg.CONF.auth.logging


def _register_common_opts():
    st2cfg.register_opts()


def _register_app_opts():
    available_backends = get_available_backends()
    auth_opts = [
        cfg.StrOpt('host', default='0.0.0.0', help='Host on which the service should listen on.'),
        cfg.IntOpt('port', default=9100, help='Port on which the service should listen on.'),
        cfg.BoolOpt('use_ssl', default=False, help='Specify to enable SSL / TLS mode'),
        cfg.StrOpt('cert', default='/etc/apache2/ssl/mycert.crt',
                   help='Path to the SSL certificate file. Only used when "use_ssl" is specified.'),
        cfg.StrOpt('key', default='/etc/apache2/ssl/mycert.key',
                   help='Path to the SSL private key file. Only used when "use_ssl" is specified.'),
        cfg.StrOpt('logging', default='conf/logging.conf',
                   help='Path to the logging config.'),
        cfg.BoolOpt('debug', default=False,
                    help='Specify to enable debug mode.'),
        cfg.StrOpt('mode', default=DEFAULT_MODE,
                   help='Authentication mode (%s)' % (','.join(VALID_MODES))),
        cfg.StrOpt('backend', default=DEFAULT_BACKEND,
                   help=('Authentication backend to use in a standalone mode. Available '
                         'backends: %s.' % (','.join(get_available_backends())))),
        cfg.StrOpt('backend_kwargs', default=None,
                   help='JSON serialized arguments which are passed to the authentication backend'
                        ' in a standalone mode.')

    ]
    cfg.CONF.register_cli_opts(auth_opts, group='auth')

    api_opts = [
        cfg.ListOpt('allow_origin', default=['http://localhost:3000'],
            help='List of origins allowed'),
    ]
    cfg.CONF.register_cli_opts(api_opts, group='api')

register_opts()
