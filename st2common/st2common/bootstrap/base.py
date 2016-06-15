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
import glob

import six

from st2common import log as logging
from st2common.constants.pack import MANIFEST_FILE_NAME
from st2common.constants.pack import CONFIG_SCHEMA_FILE_NAME
from st2common.content.loader import MetaLoader
from st2common.content.loader import ContentPackLoader
from st2common.models.api.pack import PackAPI
from st2common.models.api.pack import ConfigSchemaAPI
from st2common.persistence.pack import Pack
from st2common.persistence.pack import ConfigSchema
from st2common.util.file_system import get_file_list
from st2common.exceptions.db import StackStormDBObjectNotFoundError

__all__ = [
    'ResourceRegistrar'
]

LOG = logging.getLogger(__name__)

# Note: We use the cache to avoid manipulating the DB object for the same pack multiple times
# during the same register-content run.
# This works fine since those classes are only uses from register-content which is a script and not
# a long running process.
REGISTERED_PACKS_CACHE = {}

EXCLUDE_FILE_PATTERNS = [
    '*.pyc'
]


class ResourceRegistrar(object):
    ALLOWED_EXTENSIONS = []

    def __init__(self, use_pack_cache=True, fail_on_failure=False):
        """
        :param use_pack_cache: True to cache which packs have been registered in memory and making
                                sure packs are only registered once.
        :type use_pack_cache: ``bool``

        :param fail_on_failure: Throw an exception if resource registration fails.
        :type fail_on_failure: ``bool``
        """
        self._use_pack_cache = use_pack_cache
        self._fail_on_failure = fail_on_failure

        self._meta_loader = MetaLoader()
        self._pack_loader = ContentPackLoader()

    def get_resources_from_pack(self, resources_dir):
        resources = []
        for ext in self.ALLOWED_EXTENSIONS:
            resources_glob = resources_dir

            if resources_dir.endswith('/'):
                resources_glob = resources_dir + ext
            else:
                resources_glob = resources_dir + '/*' + ext

            resource_files = glob.glob(resources_glob)
            resources.extend(resource_files)

        resources = sorted(resources)
        return resources

    def get_registered_packs(self):
        """
        Return a list of registered packs.

        :rype: ``list``
        """
        return REGISTERED_PACKS_CACHE.keys()

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

        LOG.debug('Registering pack: %s' % (pack_name))
        REGISTERED_PACKS_CACHE[pack_name] = True

        try:
            pack_db, _ = self._register_pack(pack_name=pack_name, pack_dir=pack_dir)
        except Exception:
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

        # 2. Register corresponding pack config schema
        config_schema_db = self._register_pack_config_schema_db(pack_name=pack_name,
                                                                pack_dir=pack_dir)

        return pack_db, config_schema_db

    def _register_pack_db(self, pack_name, pack_dir):
        manifest_path = os.path.join(pack_dir, MANIFEST_FILE_NAME)

        if not os.path.isfile(manifest_path):
            raise ValueError('Pack "%s" is missing %s file' % (pack_name, MANIFEST_FILE_NAME))

        content = self._meta_loader.load(manifest_path)
        if not content:
            raise ValueError('Pack "%s" metadata file is empty' % (pack_name))

        content['ref'] = pack_name

        # Include a list of pack files
        pack_file_list = get_file_list(directory=pack_dir, exclude_patterns=EXCLUDE_FILE_PATTERNS)
        content['files'] = pack_file_list

        pack_api = PackAPI(**content)
        pack_db = PackAPI.to_model(pack_api)

        try:
            pack_db.id = Pack.get_by_ref(pack_name).id
        except StackStormDBObjectNotFoundError:
            LOG.debug('Pack %s not found. Creating new one.', pack_name)

        pack_db = Pack.add_or_update(pack_db)
        LOG.debug('Pack %s registered.' % (pack_name))
        return pack_db

    def _register_pack_config_schema_db(self, pack_name, pack_dir):
        config_schema_path = os.path.join(pack_dir, CONFIG_SCHEMA_FILE_NAME)

        if not os.path.isfile(config_schema_path):
            # Note: Config schema is optional
            return None

        content = {}
        values = self._meta_loader.load(config_schema_path)
        content['pack'] = pack_name
        content['attributes'] = values

        config_schema_api = ConfigSchemaAPI(**content)
        config_schema_db = ConfigSchemaAPI.to_model(config_schema_api)

        try:
            config_schema_db.id = ConfigSchema.get_by_pack(pack_name).id
        except StackStormDBObjectNotFoundError:
            LOG.debug('Config schema for pack %s not found. Creating new one.', pack_name)

        config_schema_db = ConfigSchema.add_or_update(config_schema_db)
        LOG.debug('Config schema for pack %s registered.' % (pack_name))
        return config_schema_db
