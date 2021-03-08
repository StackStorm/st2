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

from oslo_config import cfg

from st2common import config
from st2common import log as logging
from st2common.config import do_register_cli_opts
from st2common.script_setup import setup as common_setup
from st2common.util.pack_management import get_and_set_proxy_config
from st2common.util.virtualenvs import setup_pack_virtualenv

__all__ = ["main"]

LOG = logging.getLogger(__name__)


def _register_cli_opts():
    cli_opts = [
        cfg.MultiStrOpt(
            "pack",
            default=None,
            required=True,
            positional=True,
            help="Name of the pack to setup the virtual environment for.",
        ),
        cfg.BoolOpt(
            "update",
            default=False,
            help=(
                "Check this option if the virtual environment already exists and if you "
                "only want to perform an update and installation of new dependencies. If "
                "you don't check this option, the virtual environment will be destroyed "
                "then re-created. If you check this and the virtual environment doesn't "
                "exist, it will create it.."
            ),
        ),
    ]
    do_register_cli_opts(cli_opts)


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
    update = cfg.CONF.update

    proxy_config = get_and_set_proxy_config()

    for pack in packs:
        # Setup pack virtual environment
        LOG.info('Setting up virtualenv for pack "%s"' % (pack))
        setup_pack_virtualenv(
            pack_name=pack,
            update=update,
            logger=LOG,
            proxy_config=proxy_config,
            no_download=True,
        )
        LOG.info('Successfully set up virtualenv for pack "%s"' % (pack))

    return 0
