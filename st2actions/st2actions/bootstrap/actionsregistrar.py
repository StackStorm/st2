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
from st2common.persistence.action import Action
from st2common.models.api.action import ActionAPI
from st2common.models.system.common import ResourceReference
import st2common.content.utils as content_utils
import st2common.util.action_db as action_utils
import st2common.validators.api.action as action_validator

__all__ = [
    'ActionsRegistrar',
    'register_actions'
]

LOG = logging.getLogger(__name__)


class ActionsRegistrar(ResourceRegistrar):
    ALLOWED_EXTENSIONS = ALLOWED_EXTS

    def register_actions_from_packs(self, base_dirs):
        """
        Discover all the packs in the provided directory and register actions from all of the
        discovered packs.

        :return: Number of actions registered.
        :rtype: ``int``
        """
        registered_count = 0

        content = self._pack_loader.get_content(base_dirs=base_dirs,
                                                content_type='actions')

        for pack, actions_dir in six.iteritems(content):
            try:
                LOG.debug('Registering actions from pack %s:, dir: %s', pack, actions_dir)
                actions = self._get_actions_from_pack(actions_dir)
                count = self._register_actions_from_pack(pack=pack, actions=actions)
                registered_count += count
            except:
                LOG.exception('Failed registering all actions from pack: %s', actions_dir)

        return registered_count

    def register_actions_from_pack(self, pack_dir):
        """
        Register all the actions from the provided pack.

        :return: Number of actions registered.
        :rtype: ``int``
        """
        pack_dir = pack_dir[:-1] if pack_dir.endswith('/') else pack_dir
        _, pack = os.path.split(pack_dir)
        actions_dir = self._pack_loader.get_content_from_pack(pack_dir=pack_dir,
                                                              content_type='actions')

        registered_count = 0

        if not actions_dir:
            return registered_count

        LOG.debug('Registering actions from pack %s:, dir: %s', pack, actions_dir)

        try:
            actions = self._get_actions_from_pack(actions_dir=actions_dir)
            registered_count = self._register_actions_from_pack(pack=pack, actions=actions)
        except:
            LOG.exception('Failed registering all actions from pack: %s', actions_dir)

        return registered_count

    def _get_actions_from_pack(self, actions_dir):
        actions = self.get_resources_from_pack(resources_dir=actions_dir)

        # Exclude global actions configuration file
        config_files = ['actions/config' + ext for ext in self.ALLOWED_EXTENSIONS]

        for config_file in config_files:
            actions = [file_path for file_path in actions if config_file not in file_path]

        return actions

    def _register_action(self, pack, action):
        content = self._meta_loader.load(action)
        pack_field = content.get('pack', None)
        if not pack_field:
            content['pack'] = pack
            pack_field = pack
        if pack_field != pack:
            raise Exception('Model is in pack "%s" but field "pack" is different: %s' %
                            (pack, pack_field))

        action_api = ActionAPI(**content)
        action_api.validate()
        action_validator.validate_action(action_api)
        model = ActionAPI.to_model(action_api)

        action_ref = ResourceReference.to_string_reference(pack=pack, name=str(content['name']))
        existing = action_utils.get_action_by_ref(action_ref)
        if not existing:
            LOG.debug('Action %s not found. Creating new one with: %s', action_ref, content)
        else:
            LOG.debug('Action %s found. Will be updated from: %s to: %s',
                      action_ref, existing, model)
            model.id = existing.id

        try:
            model = Action.add_or_update(model)
            extra = {'action_db': model}
            LOG.audit('Action updated. Action %s from %s.', model, action, extra=extra)
        except Exception:
            LOG.exception('Failed to write action to db %s.', model.name)
            raise

    def _register_actions_from_pack(self, pack, actions):
        registered_count = 0

        for action in actions:
            try:
                LOG.debug('Loading action from %s.', action)
                self._register_action(pack, action)
            except Exception:
                LOG.exception('Unable to register action: %s', action)
                continue
            else:
                registered_count += 1

        return registered_count


def register_actions(packs_base_paths=None, pack_dir=None):
    if packs_base_paths:
        assert(isinstance(packs_base_paths, list))

    if not packs_base_paths:
        packs_base_paths = [content_utils.get_packs_path()]

    registrar = ActionsRegistrar()

    if pack_dir:
        result = registrar.register_actions_from_pack(pack_dir=pack_dir)
    else:
        result = registrar.register_actions_from_packs(base_dirs=packs_base_paths)

    return result
