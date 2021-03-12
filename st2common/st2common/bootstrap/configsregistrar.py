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

from __future__ import absolute_import

import os

import six
from oslo_config import cfg

from st2common import log as logging
from st2common.content import utils as content_utils
from st2common.constants.meta import ALLOWED_EXTS
from st2common.bootstrap.base import ResourceRegistrar
from st2common.models.api.pack import ConfigAPI
from st2common.persistence.pack import Config
from st2common.exceptions.db import StackStormDBObjectNotFoundError

__all__ = ["ConfigsRegistrar"]


LOG = logging.getLogger(__name__)


class ConfigsRegistrar(ResourceRegistrar):
    """
    Class for loading and registering pack configs located in
    /opt/stackstorm/configs/<pack name>.yaml
    """

    ALLOWED_EXTENSIONS = ALLOWED_EXTS

    def __init__(
        self,
        use_pack_cache=True,
        use_runners_cache=False,
        fail_on_failure=False,
        validate_configs=True,
    ):
        super(ConfigsRegistrar, self).__init__(
            use_pack_cache=use_pack_cache,
            use_runners_cache=use_runners_cache,
            fail_on_failure=fail_on_failure,
        )

        self._validate_configs = validate_configs

    def register_from_packs(self, base_dirs):
        """
        Register configs for all the available packs.
        """
        # Register packs first
        self.register_packs(base_dirs=base_dirs)

        registered_count = 0
        packs = self._pack_loader.get_packs(base_dirs=base_dirs)
        pack_names = list(packs.keys())

        for pack_name in pack_names:
            config_path = self._get_config_path_for_pack(pack_name=pack_name)

            if not os.path.isfile(config_path):
                # Config for that pack doesn't exist
                LOG.debug(
                    'No config found for pack "%s" (file "%s" is not present).',
                    pack_name,
                    config_path,
                )
                continue

            try:
                self._register_config_for_pack(pack=pack_name, config_path=config_path)
            except Exception as e:
                if self._fail_on_failure:
                    msg = 'Failed to register config "%s" for pack "%s": %s' % (
                        config_path,
                        pack_name,
                        six.text_type(e),
                    )
                    raise ValueError(msg)

                LOG.exception(
                    'Failed to register config for pack "%s": %s',
                    pack_name,
                    six.text_type(e),
                )
            else:
                registered_count += 1

        return registered_count

    def register_from_pack(self, pack_dir):
        """
        Register config for a provided pack.
        """
        pack_dir = pack_dir[:-1] if pack_dir.endswith("/") else pack_dir
        _, pack_name = os.path.split(pack_dir)

        # Register pack first
        self.register_pack(pack_name=pack_name, pack_dir=pack_dir)

        config_path = self._get_config_path_for_pack(pack_name=pack_name)
        if not os.path.isfile(config_path):
            return 0

        self._register_config_for_pack(pack=pack_name, config_path=config_path)
        return 1

    def _get_config_path_for_pack(self, pack_name):
        configs_path = os.path.join(cfg.CONF.system.base_path, "configs/")
        config_path = os.path.join(configs_path, "%s.yaml" % (pack_name))

        return config_path

    def _register_config_for_pack(self, pack, config_path):
        content = {}
        values = self._meta_loader.load(config_path)

        content["pack"] = pack
        content["values"] = values

        config_api = ConfigAPI(**content)
        config_api.validate(validate_against_schema=self._validate_configs)
        config_db = self.save_model(config_api)

        return config_db

    @staticmethod
    def save_model(config_api):
        pack = config_api.pack
        config_db = ConfigAPI.to_model(config_api)

        try:
            config_db.id = Config.get_by_pack(pack).id
        except StackStormDBObjectNotFoundError:
            LOG.debug('Config for pack "%s" not found. Creating new entry.', pack)

        try:
            config_db = Config.add_or_update(config_db)
            extra = {"config_db": config_db}
            LOG.audit('Config for pack "%s" is updated.', config_db.pack, extra=extra)
        except Exception:
            LOG.exception("Failed to save config for pack %s.", pack)
            raise

        return config_db


def register_configs(
    packs_base_paths=None,
    pack_dir=None,
    use_pack_cache=True,
    fail_on_failure=False,
    validate_configs=True,
):

    if packs_base_paths:
        if not isinstance(packs_base_paths, list):
            raise ValueError(
                "The pack base paths has a value that is not a list"
                f" (was {type(packs_base_paths)})."
            )

    if not packs_base_paths:
        packs_base_paths = content_utils.get_packs_base_paths()

    registrar = ConfigsRegistrar(
        use_pack_cache=use_pack_cache,
        fail_on_failure=fail_on_failure,
        validate_configs=validate_configs,
    )

    if pack_dir:
        result = registrar.register_from_pack(pack_dir=pack_dir)
    else:
        result = registrar.register_from_packs(base_dirs=packs_base_paths)

    return result
