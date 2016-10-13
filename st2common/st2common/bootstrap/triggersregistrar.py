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

import six

from st2common import log as logging
from st2common.constants.meta import ALLOWED_EXTS
from st2common.bootstrap.base import ResourceRegistrar
import st2common.content.utils as content_utils
from st2common.models.utils import sensor_type_utils

__all__ = [
    'TriggersRegistrar',
    'register_triggers'
]

LOG = logging.getLogger(__name__)


class TriggersRegistrar(ResourceRegistrar):
    ALLOWED_EXTENSIONS = ALLOWED_EXTS

    def register_triggers_from_packs(self, base_dirs):
        """
        Discover all the packs in the provided directory and register triggers from all of the
        discovered packs.

        :return: Number of triggers registered.
        :rtype: ``int``
        """
        # Register packs first
        self.register_packs(base_dirs=base_dirs)

        registered_count = 0
        content = self._pack_loader.get_content(base_dirs=base_dirs,
                                                content_type='triggers')

        for pack, triggers_dir in six.iteritems(content):
            if not triggers_dir:
                LOG.debug('Pack %s does not contain triggers.', pack)
                continue
            try:
                LOG.debug('Registering triggers from pack %s:, dir: %s', pack, triggers_dir)
                triggers = self._get_triggers_from_pack(triggers_dir)
                count = self._register_triggers_from_pack(pack=pack, triggers=triggers)
                registered_count += count
            except Exception as e:
                if self._fail_on_failure:
                    raise e

                LOG.exception('Failed registering all triggers from pack "%s": %s', triggers_dir,
                              str(e))

        return registered_count

    def register_triggers_from_pack(self, pack_dir):
        """
        Register all the triggers from the provided pack.

        :return: Number of triggers registered.
        :rtype: ``int``
        """
        pack_dir = pack_dir[:-1] if pack_dir.endswith('/') else pack_dir
        _, pack = os.path.split(pack_dir)
        triggers_dir = self._pack_loader.get_content_from_pack(pack_dir=pack_dir,
                                                               content_type='triggers')

        # Register pack first
        self.register_pack(pack_name=pack, pack_dir=pack_dir)

        registered_count = 0
        if not triggers_dir:
            return registered_count

        LOG.debug('Registering triggers from pack %s:, dir: %s', pack, triggers_dir)

        try:
            triggers = self._get_triggers_from_pack(triggers_dir=triggers_dir)
            registered_count = self._register_triggers_from_pack(pack=pack, triggers=triggers)
        except Exception as e:
            if self._fail_on_failure:
                raise e

            LOG.exception('Failed registering all triggers from pack "%s": %s', triggers_dir,
                          str(e))

        return registered_count

    def _get_triggers_from_pack(self, triggers_dir):
        return self.get_resources_from_pack(resources_dir=triggers_dir)

    def _register_triggers_from_pack(self, pack, triggers):
        registered_count = 0

        for trigger in triggers:
            try:
                self._register_trigger_from_pack(pack=pack, trigger=trigger)
            except Exception as e:
                if self._fail_on_failure:
                    raise e

                LOG.debug('Failed to register trigger "%s": %s', trigger, str(e))
            else:
                LOG.debug('Trigger "%s" successfully registered', trigger)
                registered_count += 1

        return registered_count

    def _register_trigger_from_pack(self, pack, trigger):
        trigger_metadata_file_path = trigger

        LOG.debug('Loading trigger from %s.', trigger_metadata_file_path)
        content = self._meta_loader.load(file_path=trigger_metadata_file_path)

        pack_field = content.get('pack', None)
        if not pack_field:
            content['pack'] = pack
            pack_field = pack
        if pack_field != pack:
            raise Exception('Model is in pack "%s" but field "pack" is different: %s' %
                            (pack, pack_field))

        trigger_types = [content]
        result = sensor_type_utils.create_trigger_types(trigger_types=trigger_types)
        return result[0] if result else None


def register_triggers(packs_base_paths=None, pack_dir=None, use_pack_cache=True,
                      fail_on_failure=False):
    if packs_base_paths:
        assert isinstance(packs_base_paths, list)

    if not packs_base_paths:
        packs_base_paths = content_utils.get_packs_base_paths()

    registrar = TriggersRegistrar(use_pack_cache=use_pack_cache,
                                  fail_on_failure=fail_on_failure)

    if pack_dir:
        result = registrar.register_triggers_from_pack(pack_dir=pack_dir)
    else:
        result = registrar.register_triggers_from_packs(base_dirs=packs_base_paths)

    return result
