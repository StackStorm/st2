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

from st2common import log as logging
from st2common.models.api.rule import RuleAPI
import st2common.operators as criteria_operators
from st2reactor.rules.datatransform import get_transformer


LOG = logging.getLogger('st2reactor.ruleenforcement.filter')


class RuleFilter(object):
    def __init__(self, trigger_instance, trigger, rule):
        self.trigger_instance = trigger_instance
        self.trigger = trigger
        self.rule = rule

    def filter(self):
        LOG.info('Validating rule %s for %s.', self.rule.id, self.trigger['name'])
        if not self.rule.enabled:
            return False

        criteria = RuleAPI.from_model(self.rule).criteria
        is_rule_applicable = True

        if criteria and not self.trigger_instance.payload:
            return False

        transform = get_transformer(self.trigger_instance.payload)

        LOG.debug('Trigger payload: %s', self.trigger_instance.payload)
        for criterion_k in criteria.keys():
            criterion_v = criteria[criterion_k]
            is_rule_applicable = self._check_criterion(criterion_k, criterion_v, transform)
            if not is_rule_applicable:
                break

        if not is_rule_applicable:
            LOG.debug('Rule %s not applicable for %s.', self.rule.id,
                      self.trigger['name'])

        return is_rule_applicable

    def _check_criterion(self, criterion_k, criterion_v, transform):
        # No payload or matching criterion_k in the payload therefore cannot apply a criteria.
        if 'pattern' not in criterion_v or criterion_v['pattern'] is None:
            return False

        try:
            payload_value = transform({'result': '{{' + criterion_k + '}}'})
        except:
            LOG.exception('Failed transforming criteria key %s', criterion_k)
            return False

        criteria_operator = ''
        criteria_pattern = criterion_v['pattern']
        if 'type' in criterion_v:
            criteria_operator = criterion_v['type']
        op_func = criteria_operators.get_operator(criteria_operator)

        return op_func(payload_value['result'], criteria_pattern)
