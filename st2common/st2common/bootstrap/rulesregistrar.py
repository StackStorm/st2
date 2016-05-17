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
from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.bootstrap.base import ResourceRegistrar
from st2common.models.api.rule import RuleAPI
from st2common.models.system.common import ResourceReference
from st2common.persistence.rule import Rule
from st2common.services.triggers import cleanup_trigger_db_for_rule, increment_trigger_ref_count
from st2common.exceptions.db import StackStormDBObjectNotFoundError
import st2common.content.utils as content_utils

__all__ = [
    'RulesRegistrar',
    'register_rules'
]

LOG = logging.getLogger(__name__)


class RulesRegistrar(ResourceRegistrar):
    ALLOWED_EXTENSIONS = ALLOWED_EXTS

    def register_rules_from_packs(self, base_dirs):
        """
        :return: Number of rules registered.
        :rtype: ``int``
        """
        # Register packs first
        self.register_packs(base_dirs=base_dirs)

        registered_count = 0
        content = self._pack_loader.get_content(base_dirs=base_dirs,
                                                content_type='rules')
        for pack, rules_dir in six.iteritems(content):
            if not rules_dir:
                LOG.debug('Pack %s does not contain rules.', pack)
                continue
            try:
                LOG.debug('Registering rules from pack: %s', pack)
                rules = self._get_rules_from_pack(rules_dir)
                count = self._register_rules_from_pack(pack, rules)
                registered_count += count
            except Exception as e:
                if self._fail_on_failure:
                    raise e

                LOG.exception('Failed registering all rules from pack: %s', rules_dir)

        return registered_count

    def register_rules_from_pack(self, pack_dir):
        """
        Register all the rules from the provided pack.

        :return: Number of rules registered.
        :rtype: ``int``
        """
        pack_dir = pack_dir[:-1] if pack_dir.endswith('/') else pack_dir
        _, pack = os.path.split(pack_dir)
        rules_dir = self._pack_loader.get_content_from_pack(pack_dir=pack_dir,
                                                            content_type='rules')

        # Register pack first
        self.register_pack(pack_name=pack, pack_dir=pack_dir)

        registered_count = 0
        if not rules_dir:
            return registered_count

        LOG.debug('Registering rules from pack %s:, dir: %s', pack, rules_dir)

        try:
            rules = self._get_rules_from_pack(rules_dir=rules_dir)
            registered_count = self._register_rules_from_pack(pack=pack, rules=rules)
        except Exception as e:
            if self._fail_on_failure:
                raise e

            LOG.exception('Failed registering all rules from pack: %s', rules_dir)

        return registered_count

    def _get_rules_from_pack(self, rules_dir):
        return self.get_resources_from_pack(resources_dir=rules_dir)

    def _register_rules_from_pack(self, pack, rules):
        registered_count = 0

        # TODO: Refactor this monstrosity
        for rule in rules:
            LOG.debug('Loading rule from %s.', rule)
            try:
                content = self._meta_loader.load(rule)
                pack_field = content.get('pack', None)
                if not pack_field:
                    content['pack'] = pack
                    pack_field = pack
                if pack_field != pack:
                    raise Exception('Model is in pack "%s" but field "pack" is different: %s' %
                                    (pack, pack_field))
                rule_api = RuleAPI(**content)
                rule_api.validate()
                rule_db = RuleAPI.to_model(rule_api)

                # Migration from rule without pack to rule with pack.
                # There might be a rule with same name but in pack `default`
                # generated in migration script. In this case, we want to
                # delete so we don't have duplicates.
                if pack_field != DEFAULT_PACK_NAME:
                    try:
                        rule_ref = ResourceReference.to_string_reference(name=content['name'],
                                                                         pack=DEFAULT_PACK_NAME)
                        LOG.debug('Looking for rule %s in pack %s', content['name'],
                                  DEFAULT_PACK_NAME)
                        existing = Rule.get_by_ref(rule_ref)
                        LOG.debug('Existing = %s', existing)
                        if existing:
                            LOG.debug('Found rule in pack default: %s; Deleting.', rule_ref)
                            Rule.delete(existing)
                    except:
                        LOG.exception('Exception deleting rule from %s pack.', DEFAULT_PACK_NAME)

                try:
                    rule_ref = ResourceReference.to_string_reference(name=content['name'],
                                                                     pack=content['pack'])
                    existing = Rule.get_by_ref(rule_ref)
                    if existing:
                        rule_db.id = existing.id
                        LOG.debug('Found existing rule: %s with id: %s', rule_ref, existing.id)
                except StackStormDBObjectNotFoundError:
                    LOG.debug('Rule %s not found. Creating new one.', rule)

                try:
                    rule_db = Rule.add_or_update(rule_db)
                    increment_trigger_ref_count(rule_api=rule_api)
                    extra = {'rule_db': rule_db}
                    LOG.audit('Rule updated. Rule %s from %s.', rule_db, rule, extra=extra)
                except Exception:
                    LOG.exception('Failed to create rule %s.', rule_api.name)

                # If there was an existing rule then the ref count was updated in
                # to_model so it needs to be adjusted down here. Also, update could
                # lead to removal of a Trigger so now is a good time for book-keeping.
                if existing:
                    cleanup_trigger_db_for_rule(existing)
            except Exception as e:
                if self._fail_on_failure:
                    raise e

                LOG.exception('Failed registering rule from %s.', rule)
            else:
                registered_count += 1

        return registered_count


def register_rules(packs_base_paths=None, pack_dir=None, use_pack_cache=True,
                   fail_on_failure=False):
    if packs_base_paths:
        assert isinstance(packs_base_paths, list)

    if not packs_base_paths:
        packs_base_paths = content_utils.get_packs_base_paths()

    registrar = RulesRegistrar(use_pack_cache=use_pack_cache,
                               fail_on_failure=fail_on_failure)

    if pack_dir:
        result = registrar.register_rules_from_pack(pack_dir=pack_dir)
    else:
        result = registrar.register_rules_from_packs(base_dirs=packs_base_paths)

    return result
