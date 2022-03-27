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

import re

import six

from st2common import log as logging
from st2common import operators as criteria_operators
from st2common.constants.rules import RULE_TYPE_BACKSTOP
from st2common.constants.rules import MATCH_CRITERIA
from st2common.constants.rule_enforcement import RULE_ENFORCEMENT_STATUS_FAILED
from st2common.models.db.rule_enforcement import RuleEnforcementDB
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.util.jsonify import json_decode

from st2common.util.payload import PayloadLookup
from st2common.util.templating import render_template_with_system_context

__all__ = ["RuleFilter"]


LOG = logging.getLogger("st2reactor.ruleenforcement.filter")


class RuleFilter(object):
    def __init__(self, trigger_instance, trigger, rule, extra_info=False):
        """
        :param trigger_instance: TriggerInstance DB object.
        :type trigger_instance: :class:`TriggerInstanceDB``

        :param trigger: Trigger DB object.
        :type trigger: :class:`TriggerDB`

        :param rule: Rule DB object.
        :type rule: :class:`RuleDB`
        """
        self.trigger_instance = trigger_instance
        self.trigger = trigger
        self.rule = rule
        self.extra_info = extra_info

        # Base context used with a logger
        self._base_logger_context = {
            "rule": self.rule,
            "trigger": self.trigger,
            "trigger_instance": self.trigger_instance,
        }

    def filter(self):
        """
        Return true if the rule is applicable to the provided trigger instance.

        :rtype: ``bool``
        """
        LOG.info(
            "Validating rule %s for %s.",
            self.rule.ref,
            self.trigger["name"],
            extra=self._base_logger_context,
        )

        if not self.rule.enabled:
            if self.extra_info:
                LOG.info(
                    "Validation failed for rule %s as it is disabled.", self.rule.ref
                )
            return False

        criteria = self.rule.criteria
        is_rule_applicable = True

        if criteria and not self.trigger_instance.payload:
            return False

        payload_lookup = PayloadLookup(self.trigger_instance.payload)

        LOG.debug(
            "Trigger payload: %s",
            self.trigger_instance.payload,
            extra=self._base_logger_context,
        )

        for (criterion_k, criterion_v) in six.iteritems(criteria):
            (
                is_rule_applicable,
                payload_value,
                criterion_pattern,
            ) = self._check_criterion(criterion_k, criterion_v, payload_lookup)
            if not is_rule_applicable:
                if self.extra_info:
                    criteria_extra_info = "\n".join(
                        [
                            "  key: %s" % criterion_k,
                            "  pattern: %s" % criterion_pattern,
                            "  type: %s" % criterion_v["type"],
                            "  payload: %s" % payload_value,
                        ]
                    )
                    LOG.info(
                        "Validation for rule %s failed on criteria -\n%s",
                        self.rule.ref,
                        criteria_extra_info,
                        extra=self._base_logger_context,
                    )
                break

        if not is_rule_applicable:
            LOG.debug(
                "Rule %s not applicable for %s.",
                self.rule.id,
                self.trigger["name"],
                extra=self._base_logger_context,
            )

        return is_rule_applicable

    def _check_criterion(self, criterion_k, criterion_v, payload_lookup):
        if "type" not in criterion_v:
            # Comparison operator type not specified, can't perform a comparison
            return (False, None, None)

        criteria_operator = criterion_v["type"]
        criteria_condition = criterion_v.get("condition", None)
        criteria_pattern = criterion_v.get("pattern", None)

        # Render the pattern (it can contain a jinja expressions)
        try:
            criteria_pattern = self._render_criteria_pattern(
                criteria_pattern=criteria_pattern,
                criteria_context=payload_lookup.context,
            )
        except Exception as e:
            msg = 'Failed to render pattern value "%s" for key "%s"' % (
                criteria_pattern,
                criterion_k,
            )
            LOG.exception(msg, extra=self._base_logger_context)
            self._create_rule_enforcement(failure_reason=msg, exc=e)

            return (False, None, None)

        # Avoids the dict unique keys limitation. Allows multiple evaluations of the same payload item by a rule.
        criterion_k_hash_strip = criterion_k.split("#", 1)[0]
        try:
            matches = payload_lookup.get_value(criterion_k_hash_strip)
            # pick value if only 1 matches else will end up being an array match.
            if matches:
                payload_value = matches[0] if len(matches) > 0 else matches
            else:
                payload_value = None
        except Exception as e:
            msg = "Failed transforming criteria key %s" % criterion_k
            LOG.exception(msg, extra=self._base_logger_context)
            self._create_rule_enforcement(failure_reason=msg, exc=e)

            return (False, None, None)

        op_func = criteria_operators.get_operator(criteria_operator)

        try:
            if criteria_operator == criteria_operators.SEARCH:
                result = op_func(
                    value=payload_value,
                    criteria_pattern=criteria_pattern,
                    criteria_condition=criteria_condition,
                    check_function=self._bool_criterion,
                )
            else:
                result = op_func(value=payload_value, criteria_pattern=criteria_pattern)
        except Exception as e:
            msg = "There might be a problem with the criteria in rule %s" % (
                self.rule.ref
            )
            LOG.exception(msg, extra=self._base_logger_context)
            self._create_rule_enforcement(failure_reason=msg, exc=e)

            return (False, None, None)

        return result, payload_value, criteria_pattern

    def _bool_criterion(self, criterion_k, criterion_v, payload_lookup):
        # Pass through to _check_criterion, but pull off and return only the
        # final result
        return self._check_criterion(criterion_k, criterion_v, payload_lookup)[0]

    def _render_criteria_pattern(self, criteria_pattern, criteria_context):
        # Note: Here we want to use strict comparison to None to make sure that
        # other falsy values such as integer 0 are handled correctly.
        if criteria_pattern is None:
            return None

        if not isinstance(criteria_pattern, six.string_types):
            # We only perform rendering if value is a string - rendering a non-string value
            # makes no sense
            return criteria_pattern

        LOG.debug(
            "Rendering criteria pattern (%s) with context: %s",
            criteria_pattern,
            criteria_context,
        )

        to_complex = False

        # Check if jinja variable is in criteria_pattern and if so lets ensure
        # the proper type is applied to it using to_complex jinja filter
        if len(re.findall(MATCH_CRITERIA, criteria_pattern)) > 0:
            LOG.debug("Rendering Complex")
            complex_criteria_pattern = re.sub(
                MATCH_CRITERIA, r"\1\2 | to_complex\3", criteria_pattern
            )

            try:
                criteria_rendered = render_template_with_system_context(
                    value=complex_criteria_pattern, context=criteria_context
                )
                criteria_rendered = json_decode(criteria_rendered)
                to_complex = True
            except ValueError as error:
                LOG.debug("Criteria pattern not valid JSON: %s", error)

        if not to_complex:
            criteria_rendered = render_template_with_system_context(
                value=criteria_pattern, context=criteria_context
            )

        LOG.debug("Rendered criteria pattern: %s", criteria_rendered)

        return criteria_rendered

    def _create_rule_enforcement(self, failure_reason, exc):
        """
        Note: We also create RuleEnforcementDB for rules which failed to match due to an exception.

        Without that, only way for users to find out about those failes matches is by inspecting
        the logs.
        """
        failure_reason = (
            'Failed to match rule "%s" against trigger instance "%s": %s: %s'
            % (
                self.rule.ref,
                str(self.trigger_instance.id),
                failure_reason,
                str(exc),
            )
        )
        rule_spec = {
            "ref": self.rule.ref,
            "id": str(self.rule.id),
            "uid": self.rule.uid,
        }
        enforcement_db = RuleEnforcementDB(
            trigger_instance_id=str(self.trigger_instance.id),
            rule=rule_spec,
            failure_reason=failure_reason,
            status=RULE_ENFORCEMENT_STATUS_FAILED,
        )

        try:
            RuleEnforcement.add_or_update(enforcement_db)
        except:
            extra = {"enforcement_db": enforcement_db}
            LOG.exception("Failed writing enforcement model to db.", extra=extra)

        return enforcement_db


class SecondPassRuleFilter(RuleFilter):
    """
    Special filter that handles all second pass rules. For not these are only
    backstop rules i.e. those that can match when no other rule has matched.
    """

    def __init__(self, trigger_instance, trigger, rule, first_pass_matched):
        """
        :param trigger_instance: TriggerInstance DB object.
        :type trigger_instance: :class:`TriggerInstanceDB``

        :param trigger: Trigger DB object.
        :type trigger: :class:`TriggerDB`

        :param rule: Rule DB object.
        :type rule: :class:`RuleDB`

        :param first_pass_matched: Rules that matched in the first pass.
        :type first_pass_matched: `list`
        """
        super(SecondPassRuleFilter, self).__init__(trigger_instance, trigger, rule)
        self.first_pass_matched = first_pass_matched

    def filter(self):
        # backstop rules only apply if no rule matched in the first pass.
        if self.first_pass_matched and self._is_backstop_rule():
            return False
        return super(SecondPassRuleFilter, self).filter()

    def _is_backstop_rule(self):
        return self.rule.type["ref"] == RULE_TYPE_BACKSTOP
