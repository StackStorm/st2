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
import glob

import six

from st2common import log as logging
from st2common.constants.pack import CONFIG_SCHEMA_FILE_NAME
from st2common.content.loader import MetaLoader
from st2common.content.loader import OverrideLoader
from st2common.content.loader import ContentPackLoader
from st2common.models.api.pack import PackAPI
from st2common.models.api.pack import ConfigSchemaAPI
from st2common.persistence.pack import Pack
from st2common.persistence.pack import ConfigSchema
from st2common.util.file_system import get_file_list
from st2common.util.pack import get_pack_metadata
from st2common.util.pack import get_pack_ref_from_metadata
from st2common.exceptions.db import StackStormDBObjectNotFoundError

__all__ = ["ResourceRegistrar"]

LOG = logging.getLogger(__name__)

# Note: We use the cache to avoid manipulating the DB object for the same pack multiple times
# during the same register-content run.
# This works fine since those classes are only uses from register-content which is a script and not
# a long running process.
REGISTERED_PACKS_CACHE = {}

EXCLUDE_FILE_PATTERNS = ["*.pyc", ".git/*"]


class ResourceRegistrar(object):
    ALLOWED_EXTENSIONS = []

    def __init__(
        self, use_pack_cache=True, use_runners_cache=False, fail_on_failure=False
    ):
        """
        :param use_pack_cache: True to cache which packs have been registered in memory and making
                                sure packs are only registered once.
        :type use_pack_cache: ``bool``

        :param use_runners_cache: True to cache RunnerTypeDB objects in memory to reduce load on
                                  the database.
        :type use_runners_cache: ``bool``

        :param fail_on_failure: Throw an exception if resource registration fails.
        :type fail_on_failure: ``bool``
        """
        self._use_pack_cache = use_pack_cache
        self._use_runners_cache = use_runners_cache
        self._fail_on_failure = fail_on_failure

        self._meta_loader = MetaLoader()
        self._override_loader = OverrideLoader()
        self._pack_loader = ContentPackLoader()

        # Maps runner name -> RunnerTypeDB
        self._runner_type_db_cache = {}

    def get_resources_from_pack(self, resources_dir):
        resources = []
        for ext in self.ALLOWED_EXTENSIONS:
            resources_glob = resources_dir

            if resources_dir.endswith("/"):
                resources_glob = resources_dir + ext
            else:
                resources_glob = resources_dir + "/*" + ext

            resource_files = glob.glob(resources_glob)
            resources.extend(resource_files)

        resources = sorted(resources)
        return resources

    def get_registered_packs(self):
        """
        Return a list of registered packs.

        :rype: ``list``
        """
        return list(REGISTERED_PACKS_CACHE.keys())

    def register_packs(self, base_dirs):
        """
        Register packs in all the provided directories.
        """
        packs = self._pack_loader.get_packs(base_dirs=base_dirs)

        registered_count = 0
        for pack_name, pack_path in six.iteritems(packs):
            self.register_pack(pack_name=pack_name, pack_dir=pack_path)
            registered_count += 1

        return registered_count

    def register_pack(self, pack_name, pack_dir):
        """
        Register pack in the provided directory.
        """
        if self._use_pack_cache and pack_name in REGISTERED_PACKS_CACHE:
            # This pack has already been registered during this register content run
            return

        LOG.debug("Registering pack: %s" % (pack_name))
        REGISTERED_PACKS_CACHE[pack_name] = True

        try:
            pack_db, _ = self._register_pack(pack_name=pack_name, pack_dir=pack_dir)
        except Exception as e:
            if self._fail_on_failure:
                msg = 'Failed to register pack "%s": %s' % (pack_name, six.text_type(e))
                raise ValueError(msg)

            LOG.exception('Failed to register pack "%s"' % (pack_name))
            return None

        return pack_db

    def _register_pack(self, pack_name, pack_dir):
        """
        Register a pack and corresponding pack config schema (create a DB object in the system).

        Note: Pack registration now happens when registering the content and not when installing
        a pack using packs.install. Eventually this will be moved to the pack management API.
        """
        # 1. Register pack
        pack_db = self._register_pack_db(pack_name=pack_name, pack_dir=pack_dir)

        # Display a warning if pack contains deprecated config.yaml file. Support for those files
        # will be fully removed in v2.4.0.
        config_path = os.path.join(pack_dir, "config.yaml")
        if os.path.isfile(config_path):
            LOG.error(
                'Pack "%s" contains a deprecated config.yaml file (%s). '
                'Support for "config.yaml" files has been deprecated in StackStorm v1.6.0 '
                "in favor of config.schema.yaml config schema files and config files in "
                "/opt/stackstorm/configs/ directory. Support for config.yaml files has "
                "been removed in the release (v2.4.0) so please migrate. For more "
                "information please refer to %s "
                % (
                    pack_db.name,
                    config_path,
                    "https://docs.stackstorm.com/reference/pack_configs.html",
                )
            )

        # 2. Register corresponding pack config schema
        config_schema_db = self._register_pack_config_schema_db(
            pack_name=pack_name, pack_dir=pack_dir
        )

        return pack_db, config_schema_db

    def _register_pack_db(self, pack_name, pack_dir):
        content = get_pack_metadata(pack_dir=pack_dir)

        # The rules for the pack ref are as follows:
        # 1. If ref attribute is available, we used that
        # 2. If pack_name is available we use that (this only applies to packs
        # 2hich are in sub-directories)
        # 2. If attribute is not available, but pack name is and pack name meets the valid name
        # criteria, we use that
        content["ref"] = get_pack_ref_from_metadata(
            metadata=content, pack_directory_name=pack_name
        )

        # Include a list of pack files
        pack_file_list = get_file_list(
            directory=pack_dir, exclude_patterns=EXCLUDE_FILE_PATTERNS
        )
        content["files"] = pack_file_list
        content["path"] = pack_dir

        pack_api = PackAPI(**content)
        pack_api.validate()
        pack_db = PackAPI.to_model(pack_api)

        try:
            pack_db.id = Pack.get_by_ref(content["ref"]).id
        except StackStormDBObjectNotFoundError:
            LOG.debug("Pack %s not found. Creating new one.", pack_name)

        pack_db = Pack.add_or_update(pack_db)
        LOG.debug("Pack %s registered." % (pack_name))
        return pack_db

    def _register_pack_config_schema_db(self, pack_name, pack_dir):
        config_schema_path = os.path.join(pack_dir, CONFIG_SCHEMA_FILE_NAME)

        if not os.path.isfile(config_schema_path):
            # Note: Config schema is optional
            return None

        values = self._meta_loader.load(config_schema_path)

        if not values:
            raise ValueError(
                'Config schema "%s" is empty and invalid.' % (config_schema_path)
            )

        content = {}
        content["pack"] = pack_name
        content["attributes"] = values

        config_schema_api = ConfigSchemaAPI(**content)
        config_schema_api = config_schema_api.validate()
        config_schema_db = ConfigSchemaAPI.to_model(config_schema_api)

        try:
            config_schema_db.id = ConfigSchema.get_by_pack(pack_name).id
        except StackStormDBObjectNotFoundError:
            LOG.debug(
                "Config schema for pack %s not found. Creating new one.", pack_name
            )

        config_schema_db = ConfigSchema.add_or_update(config_schema_db)
        LOG.debug("Config schema for pack %s registered." % (pack_name))
        return config_schema_db
