# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from os import listdir

from oslo_config import cfg

from st2common import config
from st2common import log as logging
from st2common.config import do_register_cli_opts
from st2common.script_setup import setup as common_setup
from st2common.util.pack import get_pack_metadata
from st2common.util.pack_management import download_pack
from st2common.util.pack_management import get_and_set_proxy_config
from st2common.util.virtualenvs import setup_pack_virtualenv
from st2common.content.utils import get_pack_base_path, get_packs_base_paths

__all__ = ["main"]

LOG = logging.getLogger(__name__)


def _register_cli_opts():
    cli_opts = [
        cfg.MultiStrOpt(
            "pack",
            default=None,
            required=True,
            positional=True,
            help="Name of the pack to install.",
        ),
        cfg.BoolOpt(
            "verify-ssl",
            default=True,
            help=(
                "Verify SSL certificate of the Git repo from which the pack is "
                "downloaded."
            ),
        ),
        cfg.BoolOpt(
            "force",
            default=False,
            help="True to force pack installation and ignore install "
            "lock file if it exists.",
        ),
        cfg.BoolOpt(
            "get-dependencies",
            default=False,
            help="True to install pack dependencies",
        ),
    ]
    do_register_cli_opts(cli_opts)


def get_pack_dependencies(pack, verify_ssl, force, dependencies, proxy_config):
    pack_path = get_pack_base_path(pack)

    try:
        pack_metadata = get_pack_metadata(pack_dir=pack_path)
        result = pack_metadata.get("dependencies", None)
        if result:
            LOG.info('Getting pack dependencies for pack "%s"' % (pack))
            download_packs(result, verify_ssl, force, dependencies, proxy_config)
            LOG.info('Successfully got pack dependencies for pack "%s"' % (pack))
    except IOError:
        LOG.error("Could not open pack.yaml at location %s" % pack_path)
        result = None


def download_packs(packs, verify_ssl, force, dependencies, proxy_config):
    packs_base_paths = get_packs_base_paths()

    for pack in packs:
        for pack_dir in packs_base_paths:
            if pack in listdir(pack_dir):
                LOG.info('Pack (%s) already installed in "%s"' % (pack, pack_dir))
                break
        else:
            # 1. Download the pack
            LOG.info('Installing pack "%s"' % (pack))
            result = download_pack(
                pack=pack,
                verify_ssl=verify_ssl,
                force=force,
                proxy_config=proxy_config,
                force_permissions=True,
            )

            # Raw pack name excluding the version
            pack_name = result[1]
            success = result[2][0]

            if success:
                LOG.info('Successfully installed pack "%s"' % (pack_name))
            else:
                error = result[2][1]
                LOG.error('Failed to install pack "%s": %s' % (pack_name, error))
                sys.exit(2)

            # 2. Setup pack virtual environment
            LOG.info('Setting up virtualenv for pack "%s"' % (pack_name))
            setup_pack_virtualenv(
                pack_name=pack_name,
                update=False,
                logger=LOG,
                proxy_config=proxy_config,
                no_download=True,
            )
            LOG.info('Successfully set up virtualenv for pack "%s"' % (pack_name))

            if dependencies:
                get_pack_dependencies(
                    pack_name, verify_ssl, force, dependencies, proxy_config
                )


def main(argv):
    _register_cli_opts()

    # Parse CLI args, set up logging
    common_setup(
        config=config,
        setup_db=False,
        register_mq_exchanges=False,
        register_internal_trigger_types=False,
    )

    packs = cfg.CONF.pack
    verify_ssl = cfg.CONF.verify_ssl
    force = cfg.CONF.force
    dependencies = cfg.CONF.get_dependencies

    proxy_config = get_and_set_proxy_config()

    download_packs(packs, verify_ssl, force, dependencies, proxy_config)

    return 0
