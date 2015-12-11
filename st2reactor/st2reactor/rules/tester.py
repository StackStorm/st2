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

from st2common import log as logging
from st2common.content.loader import MetaLoader
from st2common.models.db.rule import RuleDB
from st2common.models.db.trigger import TriggerDB
from st2common.models.db.trigger import TriggerInstanceDB
from st2common.models.system.common import ResourceReference
from st2common.persistence.reactor import Rule, TriggerInstance, Trigger

from st2reactor.rules.matcher import RulesMatcher

__all__ = [
    'RuleTester'
]

LOG = logging.getLogger(__name__)


class RuleTester(object):
    def __init__(self, rule_file_path, rule_ref, trigger_instance_file_path, trigger_instance_id):
        """
        :param rule_file_path: Path to the file containing rule definition.
        :type rule_file_path: ``str``

        :param trigger_instance_file_path: Path to the file containg trigger instance definition.
        :type trigger_instance_file_path: ``str``
        """
        self._rule_file_path = rule_file_path
        self._rule_ref = rule_ref
        self._trigger_instance_file_path = trigger_instance_file_path
        self._trigger_instance_id = trigger_instance_id
        self._meta_loader = MetaLoader()

    def evaluate(self):
        """
        Evaluate trigger instance against the rule.

        :return: ``True`` if the rule matches, ``False`` otherwise.
        :rtype: ``boolean``
        """

        rule_db = self._get_rule_db()
        trigger_instance_db, trigger_db = self._get_trigger_instance_db()

        # The trigger check needs to be performed here as that is not performed
        # by RulesMatcher.
        if rule_db.trigger != trigger_db.ref:
            LOG.info('rule.trigger "%s" and trigger.ref "%s" do not match.',
                     rule_db.trigger, trigger_db.ref)
            return False

        matcher = RulesMatcher(trigger_instance=trigger_instance_db, trigger=trigger_db,
                               rules=[rule_db], extra_info=True)
        matching_rules = matcher.get_matching_rules()

        return len(matching_rules) >= 1

    def _get_rule_db(self):
        if self._rule_file_path:
            return self._get_rule_db_from_file(
                file_path=os.path.realpath(self._rule_file_path))
        elif self._rule_ref:
            return Rule.get_by_ref(self._rule_ref)
        raise ValueError('One of _rule_file_path or _rule_ref should be specified.')

    def _get_trigger_instance_db(self):
        if self._trigger_instance_file_path:
            return self._get_trigger_instance_db_from_file(
                file_path=os.path.realpath(self._trigger_instance_file_path))
        elif self._trigger_instance_id:
            trigger_instance_db = TriggerInstance.get_by_id(self._trigger_instance_id)
            trigger_db = Trigger.get_by_ref(trigger_instance_db.trigger)
            return trigger_instance_db, trigger_db
        raise ValueError('One of _trigger_instance_file_path or'
                         '_trigger_instance_id should be specified.')

    def _get_rule_db_from_file(self, file_path):
        data = self._meta_loader.load(file_path=file_path)
        pack = data.get('pack', 'unknown')
        name = data.get('name', 'unknown')
        trigger = data['trigger']['type']
        criteria = data.get('criteria', None)

        rule_db = RuleDB(pack=pack, name=name, trigger=trigger, criteria=criteria, action={},
                         enabled=True)
        return rule_db

    def _get_trigger_instance_db_from_file(self, file_path):
        data = self._meta_loader.load(file_path=file_path)
        instance = TriggerInstanceDB(**data)

        trigger_ref = ResourceReference.from_string_reference(instance['trigger'])
        trigger_db = TriggerDB(pack=trigger_ref.pack, name=trigger_ref.name, type=trigger_ref.ref)
        return instance, trigger_db
