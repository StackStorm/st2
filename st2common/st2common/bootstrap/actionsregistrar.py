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

from __future__ import absolute_import
import os
import re

import six
import jsonschema

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

    def __init__(self, use_pack_cache=True, use_runners_cache=False, fail_on_failure=False):
        super(ActionsRegistrar, self).__init__(
            use_pack_cache=use_pack_cache,
            use_runners_cache=use_runners_cache,
            fail_on_failure=fail_on_failure,
            st2_model=Action)

    def register_from_packs(self, base_dirs):
        """
        Discover all the packs in the provided directory and register actions from all of the
        discovered packs.

        :return: Number of actions registered.
        :rtype: ``int``
        """
        # Register packs first
        self.register_packs(base_dirs=base_dirs)
        LOG.debug("Cache contents: %s", self._db_content_cache)

        registered_count = 0
        all_action_db_upserts = []
        content = self._pack_loader.get_content(base_dirs=base_dirs,
                                                content_type='actions')
        for pack, actions_dir in six.iteritems(content):
            if not actions_dir:
                LOG.debug('Pack %s does not contain actions.', pack)
                continue
            try:
                LOG.debug('Registering actions from pack %s:, dir: %s', pack, actions_dir)
                actions = self._get_actions_from_pack(actions_dir)
                action_db_upserts = self._get_action_db_models(pack=pack, actions=actions)
                all_action_db_upserts.extend(action_db_upserts)
            except Exception as e:
                if self._fail_on_failure:
                    raise e

                LOG.exception('Failed registering all actions from pack: %s', actions_dir)

        registered_count = 0
        try:
            LOG.debug('Actions to persist to disk: %s', all_action_db_upserts)
            Action.bulk_upsert(all_action_db_upserts)
            registered_count = len(action_db_upserts)
        except Exception as e:
            LOG.exception('Not all actions were successfully persisted.')
            registered_count = 0

        return registered_count

    def register_from_pack(self, pack_dir):
        """
        Register all the actions from the provided pack.

        :return: Number of actions registered.
        :rtype: ``int``
        """
        pack_dir = pack_dir[:-1] if pack_dir.endswith('/') else pack_dir
        _, pack = os.path.split(pack_dir)
        actions_dir = self._pack_loader.get_content_from_pack(pack_dir=pack_dir,
                                                              content_type='actions')

        # Register pack first
        self.register_pack(pack_name=pack, pack_dir=pack_dir)

        registered_count = 0
        if not actions_dir:
            return registered_count

        LOG.debug('Registering actions from pack %s:, dir: %s', pack, actions_dir)

        try:
            actions = self._get_actions_from_pack(actions_dir=actions_dir)
            action_db_upserts = self._get_action_db_models(pack=pack, actions=actions)
        except Exception as e:
            if self._fail_on_failure:
                raise e

            LOG.exception('Failed registering all actions from pack: %s', actions_dir)

        registered_count = 0
        try:
            LOG.debug('Actions to persist to disk: %s', action_db_upserts)
            Action.bulk_upsert(action_db_upserts)
            registered_count = len(action_db_upserts)
        except Exception as e:
            LOG.exception('Not all actions were successfully persisted.')
            registered_count = 0

        return registered_count

    def _get_actions_from_pack(self, actions_dir):
        actions = self.get_resources_from_pack(resources_dir=actions_dir)

        # Exclude global actions configuration file
        config_files = ['actions/config' + ext for ext in self.ALLOWED_EXTENSIONS]

        for config_file in config_files:
            actions = [file_path for file_path in actions if config_file not in file_path]

        return actions

    def _get_action_db_model(self, pack, action):
        content = self._meta_loader.load(action)
        pack_field = content.get('pack', None)
        if not pack_field:
            content['pack'] = pack
            pack_field = pack
        if pack_field != pack:
            raise Exception('Model is in pack "%s" but field "pack" is different: %s' %
                            (pack, pack_field))

        action_api = ActionAPI(**content)

        try:
            action_api.validate()
        except jsonschema.ValidationError as e:
            # We throw a more user-friendly exception on invalid parameter name
            msg = str(e)

            is_invalid_parameter_name = 'does not match any of the regexes: ' in msg

            if is_invalid_parameter_name:
                match = re.search('\'(.+?)\' does not match any of the regexes', msg)

                if match:
                    parameter_name = match.groups()[0]
                else:
                    parameter_name = 'unknown'

                new_msg = ('Parameter name "%s" is invalid. Valid characters for parameter name '
                           'are [a-zA-Z0-0_].' % (parameter_name))
                new_msg += '\n\n' + msg
                raise jsonschema.ValidationError(new_msg)
            raise e

        # Use in-memory cached RunnerTypeDB objects to reduce load on the database
        if self._use_runners_cache:
            runner_type_db = self._runner_type_db_cache.get(action_api.runner_type, None)

            if not runner_type_db:
                runner_type_db = action_validator.get_runner_model(action_api)
                self._runner_type_db_cache[action_api.runner_type] = runner_type_db
        else:
            runner_type_db = None

        action_validator.validate_action(action_api, runner_type_db=runner_type_db)
        model = ActionAPI.to_model(action_api)

        action_ref = ResourceReference.to_string_reference(pack=pack, name=str(content['name']))
        # existing = action_utils.get_action_by_ref(action_ref)
        try:
            existing = self._db_content_cache[pack][action_ref]
        except KeyError:
            existing = None

        if not existing:
            LOG.debug('Action %s not found. Creating new one with: %s', action_ref, content)
        else:
            LOG.debug('Action %s found. Will be updated from: %s to: %s',
                      action_ref, existing, model)
            model.id = existing

        return model

    def _get_action_db_models(self, pack, actions):
        action_db_upserts = []

        for action in actions:
            action_db_model = self._get_action_db_model(pack, action)
            action_db_upserts.append(action_db_model)

        return action_db_upserts

def register_actions(packs_base_paths=None, pack_dir=None, use_pack_cache=True,
                     fail_on_failure=False):
    if packs_base_paths:
        assert isinstance(packs_base_paths, list)

    if not packs_base_paths:
        packs_base_paths = content_utils.get_packs_base_paths()

    registrar = ActionsRegistrar(use_pack_cache=use_pack_cache,
                                 fail_on_failure=fail_on_failure)

    if pack_dir:
        LOG.debug('Registering from pack dir: %s', pack_dir)
        result = registrar.register_from_pack(pack_dir=pack_dir)
    else:
        LOG.debug('Registering from dirs: %s', packs_base_paths)
        result = registrar.register_from_packs(base_dirs=packs_base_paths)

    return result
