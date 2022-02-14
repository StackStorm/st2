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

import st2common.content.utils as content_utils

from st2common import log as logging
from st2common.constants.meta import ALLOWED_EXTS
from st2common.bootstrap.base import ResourceRegistrar
from st2common.models.api.action import ActionAliasAPI
from st2common.persistence.action import Action
from st2common.persistence.actionalias import ActionAlias
from st2common.exceptions.db import StackStormDBObjectNotFoundError

__all__ = ["AliasesRegistrar", "register_aliases"]

LOG = logging.getLogger(__name__)


class AliasesRegistrar(ResourceRegistrar):
    ALLOWED_EXTENSIONS = ALLOWED_EXTS

    def register_from_packs(self, base_dirs):
        """
        Discover all the packs in the provided directory and register aliases from all of the
        discovered packs.

        :return: Tuple, Number of aliases registered, overridden.
        :rtype: ``tuple``
        """
        # Register packs first
        self.register_packs(base_dirs=base_dirs)

        registered_count = 0
        overridden_count = 0
        content = self._pack_loader.get_content(
            base_dirs=base_dirs, content_type="aliases"
        )

        for pack, aliases_dir in six.iteritems(content):
            if not aliases_dir:
                LOG.debug("Pack %s does not contain aliases.", pack)
                continue
            try:
                LOG.debug(
                    "Registering aliases from pack %s:, dir: %s", pack, aliases_dir
                )
                aliases = self._get_aliases_from_pack(aliases_dir)
                count, overridden = self._register_aliases_from_pack(
                    pack=pack, aliases=aliases
                )
                registered_count += count
                overridden_count += overridden
            except Exception as e:
                if self._fail_on_failure:
                    raise e

                LOG.exception(
                    "Failed registering all aliases from pack: %s", aliases_dir
                )

        return registered_count, overridden_count

    def register_from_pack(self, pack_dir):
        """
        Register all the aliases from the provided pack.

        :return: Tuple, Number of aliases registered, overridden
        :rtype: ``tuple``
        """
        pack_dir = pack_dir[:-1] if pack_dir.endswith("/") else pack_dir
        _, pack = os.path.split(pack_dir)
        aliases_dir = self._pack_loader.get_content_from_pack(
            pack_dir=pack_dir, content_type="aliases"
        )

        # Register pack first
        self.register_pack(pack_name=pack, pack_dir=pack_dir)

        registered_count = 0
        overridden_count = 0
        if not aliases_dir:
            return registered_count, overridden_count

        LOG.debug("Registering aliases from pack %s:, dir: %s", pack, aliases_dir)

        try:
            aliases = self._get_aliases_from_pack(aliases_dir=aliases_dir)
            registered_count, overridden_count = self._register_aliases_from_pack(
                pack=pack, aliases=aliases
            )
        except Exception as e:
            if self._fail_on_failure:
                raise e

            LOG.exception("Failed registering all aliases from pack: %s", aliases_dir)
            return registered_count, overridden_count

        return registered_count, overridden_count

    def _get_aliases_from_pack(self, aliases_dir):
        return self.get_resources_from_pack(resources_dir=aliases_dir)

    def _get_action_alias_db(
        self, pack, action_alias, ignore_metadata_file_error=False
    ):
        """
        Retrieve ActionAliasDB object.

        :param ignore_metadata_file_error: True to ignore the error when we can't infer
                                            metadata_file attribute (e.g. inside tests).
        :type ignore_metadata_file_error: ``bool``
        """
        content = self._meta_loader.load(action_alias)
        pack_field = content.get("pack", None)
        if not pack_field:
            content["pack"] = pack
            pack_field = pack
        if pack_field != pack:
            raise Exception(
                'Model is in pack "%s" but field "pack" is different: %s'
                % (pack, pack_field)
            )

        # Add in "metadata_file" attribute which stores path to the pack metadata file relative to
        # the pack directory
        try:
            metadata_file = content_utils.get_relative_path_to_pack_file(
                pack_ref=pack, file_path=action_alias, use_pack_cache=True
            )
        except ValueError as e:
            if not ignore_metadata_file_error:
                raise e
        else:
            content["metadata_file"] = metadata_file

        # Pass override information
        altered = self._override_loader.override(pack, "aliases", content)

        action_alias_api = ActionAliasAPI(**content)
        action_alias_api.validate()
        action_alias_db = ActionAliasAPI.to_model(action_alias_api)

        return action_alias_db, altered

    def _register_action_alias(self, pack, action_alias):
        action_alias_db, altered = self._get_action_alias_db(
            pack=pack, action_alias=action_alias
        )

        try:
            action_alias_db.id = ActionAlias.get_by_name(action_alias_db.name).id
        except StackStormDBObjectNotFoundError:
            LOG.debug("ActionAlias %s not found. Creating new one.", action_alias)

        action_ref = action_alias_db.action_ref

        action_db = Action.get_by_ref(action_ref)
        if not action_db:
            LOG.warning(
                "Action %s not found in DB. Did you forget to register the action?",
                action_ref,
            )

        try:
            action_alias_db = ActionAlias.add_or_update(action_alias_db)
            extra = {"action_alias_db": action_alias_db}
            LOG.audit(
                "Action alias updated. Action alias %s from %s.",
                action_alias_db,
                action_alias,
                extra=extra,
            )
        except Exception:
            LOG.exception("Failed to create action alias %s.", action_alias_db.name)
            raise
        return altered

    def _register_aliases_from_pack(self, pack, aliases):
        registered_count = 0
        overridden_count = 0

        for alias in aliases:
            try:
                LOG.debug("Loading alias from %s.", alias)
                altered = self._register_action_alias(pack, alias)
                if altered:
                    overridden_count += 1
            except Exception as e:
                if self._fail_on_failure:
                    msg = 'Failed to register alias "%s" from pack "%s": %s' % (
                        alias,
                        pack,
                        six.text_type(e),
                    )
                    raise ValueError(msg)

                LOG.exception("Unable to register alias: %s", alias)
                continue
            else:
                registered_count += 1

        return registered_count, overridden_count


def register_aliases(
    packs_base_paths=None, pack_dir=None, use_pack_cache=True, fail_on_failure=False
):

    if packs_base_paths:
        if not isinstance(packs_base_paths, list):
            raise TypeError(
                "The pack base paths has a value that is not a list"
                f" (was {type(packs_base_paths)})."
            )

    if not packs_base_paths:
        packs_base_paths = content_utils.get_packs_base_paths()

    registrar = AliasesRegistrar(
        use_pack_cache=use_pack_cache, fail_on_failure=fail_on_failure
    )

    if pack_dir:
        result = registrar.register_from_pack(pack_dir=pack_dir)
    else:
        result = registrar.register_from_packs(base_dirs=packs_base_paths)

    return result
