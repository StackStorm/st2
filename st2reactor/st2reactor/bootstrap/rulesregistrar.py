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

import glob

from oslo.config import cfg
import six

from st2common import log as logging
from st2common.constants.meta import ALLOWED_EXTS
from st2common.content.loader import (ContentPackLoader, MetaLoader)
from st2common.models.api.rule import RuleAPI
from st2common.persistence.reactor import Rule

LOG = logging.getLogger(__name__)


class RulesRegistrar(object):
    def __init__(self):
        self._meta_loader = MetaLoader()

    def _get_rules_from_pack(self, rules_dir):
        rules = []
        for ext in ALLOWED_EXTS:
            rules_ext = glob.glob(rules_dir + '/*' + ext)
            rules.extend(rules_ext)
        return rules

    def _register_rules_from_pack(self, pack, rules):
        for rule in rules:
            LOG.debug('Loading rule from %s.', rule)
            try:
                content = self._meta_loader.load(rule)
                rule_api = RuleAPI(**content)
                rule_db = RuleAPI.to_model(rule_api)
                try:
                    rule_db.id = Rule.get_by_name(rule_api.name).id
                except ValueError:
                    LOG.info('Rule %s not found. Creating new one.', rule)
                try:
                    rule_db = Rule.add_or_update(rule_db)
                    LOG.audit('Rule updated. Rule %s from %s.', rule_db, rule)
                except Exception:
                    LOG.exception('Failed to create rule %s.', rule_api.name)
            except:
                LOG.exception('Failed registering rule from %s.', rule)

    def register_rules_from_packs(self, base_dir):
        pack_loader = ContentPackLoader()
        dirs = pack_loader.get_content(base_dir=base_dir,
                                       content_type='rules')
        for pack, rules_dir in six.iteritems(dirs):
            try:
                LOG.info('Registering rules from pack: %s', pack)
                rules = self._get_rules_from_pack(rules_dir)
                self._register_rules_from_pack(pack, rules)
            except:
                LOG.exception('Failed registering all rules from pack: %s', rules_dir)


def register_rules(packs_base_path=None):
    if not packs_base_path:
        packs_base_path = cfg.CONF.content.packs_base_path
    return RulesRegistrar().register_rules_from_packs(packs_base_path)
