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

from st2common.constants.meta import PARSER_FUNCS
from st2common.models.db.reactor import RuleDB
from st2common.models.db.reactor import TriggerDB
from st2common.models.db.reactor import TriggerInstanceDB
from st2common.models.system.common import ResourceReference
from st2reactor.rules.matcher import RulesMatcher

__all__ = [
    'RuleTester'
]


class RuleTester(object):
    def __init__(self, rule_file_path, trigger_instance_file_path):
        """
        :param rule_file_path: Path to the file containing rule definition.
        :type rule_file_path: ``str``

        :param trigger_instance_file_path: Path to the file containg trigger instance definition.
        :type trigger_instance_file_path: ``str``
        """
        self._rule_file_path = rule_file_path
        self._trigger_instance_file_path = trigger_instance_file_path

    def evaluate(self):
        """
        Evaluate trigger instance against the rule.

        :return: ``True`` if the rule matches, ``False`` otherwise.
        :rtype: ``boolean``
        """
        rule_db = self._get_rule_db_from_file(file_path=self._rule_file_path)
        trigger_instance_db = \
            self._get_trigger_instance_db_from_file(file_path=self._trigger_instance_file_path)

        trigger_ref = ResourceReference.from_string_reference(trigger_instance_db['trigger'])

        trigger_db = TriggerDB()
        trigger_db.pack = trigger_ref.pack
        trigger_db.name = trigger_ref.name
        trigger_db.type = trigger_ref.ref

        matcher = RulesMatcher(trigger_instance=trigger_instance_db, trigger=trigger_db,
                               rules=[rule_db])
        matching_rules = matcher.get_matching_rules()
        return len(matching_rules) >= 1

    def _get_rule_db_from_file(self, file_path):
        data = self._get_obj_from_file(file_path=file_path)
        rule_db = RuleDB()
        rule_db.trigger = data['trigger']['type']
        rule_db.criteria = data.get('criteria', None)
        rule_db.action = {}
        rule_db.enabled = True
        return rule_db

    def _get_trigger_instance_db_from_file(self, file_path):
        data = self._get_obj_from_file(file_path=file_path)
        instance = TriggerInstanceDB(**data)
        return instance

    def _get_obj_from_file(self, file_path):
        _, file_ext = os.path.splitext(file_path)
        parser_func = PARSER_FUNCS[file_ext]

        with open(file_path, 'r') as fp:
            content = fp.read()

        data = parser_func(content)
        return data
