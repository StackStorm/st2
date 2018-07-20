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

from oslo_config import cfg

from st2common import config
from st2common import log as logging
from st2common.script_setup import setup as common_setup
from st2common.util.pack_management import download_pack
from st2common.util.virtualenvs import setup_pack_virtualenv

__all__ = [
    'main'
]

LOG = logging.getLogger(__name__)


def _do_register_cli_opts(opts, ignore_errors=False):
    for opt in opts:
        try:
            cfg.CONF.register_cli_opt(opt)
        except:
            if not ignore_errors:
                raise


def _register_cli_opts():
    cli_opts = [
        cfg.StrOpt('pack', default=None, required=True,
                   help='Name of the pack to install.'),
        cfg.BoolOpt('verify-ssl', default=True,
                   help=('Verify SSL certificate of the Git repo from which the pack is '
                         'downloaded.')),
        cfg.BoolOpt('force', default=False,
                    help='True to force pack installation and ignore install '
                         'lock file if it exists.'),
    ]
    _do_register_cli_opts(cli_opts)


def get_and_set_proxy_config():
    https_proxy = os.environ.get('https_proxy', None)
    http_proxy = os.environ.get('http_proxy', None)
    proxy_ca_bundle_path = os.environ.get('proxy_ca_bundle_path', None)
    no_proxy = os.environ.get('no_proxy', None)

    proxy_config = {}

    if http_proxy or https_proxy:
        LOG.debug('Using proxy %s', http_proxy if http_proxy else https_proxy)

        proxy_config = {
            'https_proxy': https_proxy,
            'http_proxy': http_proxy,
            'proxy_ca_bundle_path': proxy_ca_bundle_path,
            'no_proxy': no_proxy
        }

    if https_proxy and not os.environ.get('https_proxy', None):
        os.environ['https_proxy'] = https_proxy

    if http_proxy and not os.environ.get('http_proxy', None):
        os.environ['http_proxy'] = http_proxy

    if no_proxy and not os.environ.get('no_proxy', None):
        os.environ['no_proxy'] = no_proxy

    if proxy_ca_bundle_path and not os.environ.get('proxy_ca_bundle_path', None):
        os.environ['no_proxy'] = no_proxy

    return proxy_config


def main(argv):
    _register_cli_opts()

    # Parse CLI args, set up logging
    common_setup(config=config, setup_db=False, register_mq_exchanges=False,
                 register_internal_trigger_types=False)

    pack = cfg.CONF.pack
    verify_ssl = cfg.CONF.verify_ssl
    force = cfg.CONF.force

    proxy_config = get_and_set_proxy_config()

    # 1. Download the pac
    LOG.info('Installing pack "%s"' % (pack))
    result = download_pack(pack=pack, verify_ssl=verify_ssl, force=force,
                           proxy_config=proxy_config, force_permissions=True)

    success = result[2][0]

    if success:
        LOG.info('Successfuly installed pack "%s"' % (pack))
    else:
        error = result[2][1]
        LOG.error('Failed to install pack "%s": %s' % (pack, error))
        sys.exit(2)

    # 2. Setup pack virtual environment
    LOG.info('Setting up virtualenv for pack "%s"' % (pack))
    setup_pack_virtualenv(pack_name=pack, update=False, logger=LOG,
                          proxy_config=proxy_config, use_python3=False,
                          no_download=True)
    LOG.info('Successfuly set up virtualenv for pack "%s"' % (pack))
