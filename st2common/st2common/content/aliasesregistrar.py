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

import st2common.content.utils as content_utils

from st2common import log as logging
from st2common.constants.meta import ALLOWED_EXTS
from st2common.bootstrap.base import ResourceRegistrar
from st2common.models.api.action import ActionAliasAPI
from st2common.persistence.action import ActionAlias
from st2common.util.url import get_file_uri

__all__ = [
    'AliasesRegistrar',
    'register_aliases'
]

LOG = logging.getLogger(__name__)


class AliasesRegistrar(ResourceRegistrar):
    ALLOWED_EXTENSIONS = ALLOWED_EXTS

    def register_aliases_from_dirs(self, aliases_dirs=None):
        if not aliases_dirs:
            return 0
        result = 0
        for aliases_dir in aliases_dirs:
            result += self.register_aliases_from_dir(aliases_dir=aliases_dir)
        return result

    def register_aliases_from_dir(self, aliases_dir=None):
        if not aliases_dir:
            return 0
        resources = self._get_resources_from_pack(resources_dir=aliases_dir)
        return self._register_aliases(aliases=resources)

    def _register_aliases(self, aliases=None):
        registered_count = 0

        for alias in aliases:
            LOG.debug('Loading alias from %s.', alias)
            try:
                content = self._meta_loader.load(alias)
                action_alias_api = ActionAliasAPI(**content)
                action_alias_db = ActionAliasAPI.to_model(action_alias_api)
                action_alias_db.file_uri = get_file_uri(alias)

                try:
                    action_alias_db.id = ActionAlias.get_by_name(action_alias_api.name).id
                except ValueError:
                    LOG.info('ActionAlias %s not found. Creating new one.', alias)

                try:
                    action_alias_db = ActionAlias.add_or_update(action_alias_db)
                    extra = {'action_alias_db': action_alias_db}
                    LOG.audit('Action alias updated. Action alias %s from %s.', action_alias_db,
                              alias, extra=extra)
                except Exception:
                    LOG.exception('Failed to create action alias %s.', action_alias_api.name)

            except Exception:
                LOG.exception('Failed registering alias from %s.', alias)
            else:
                registered_count += 1

        return registered_count


def register_aliases(aliases_base_paths=None, aliases_dir=None):
    if aliases_base_paths:
        assert(isinstance(aliases_base_paths, list))

    registrar = AliasesRegistrar()

    if aliases_dir:
        result = registrar.register_aliases_from_dir(aliases_dir=aliases_dir)
    else:
        if not aliases_base_paths:
            aliases_base_paths = content_utils.get_aliases_base_paths()
        result = registrar.register_aliases_from_dirs(aliases_dirs=aliases_base_paths)

    return result
