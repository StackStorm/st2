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
import six

from st2common import log as logging
from st2common.persistence.rule import Rule


LOG = logging.getLogger(__name__)

__all__ = ["get_rules_given_trigger", "get_rules_with_trigger_ref"]


def get_rules_given_trigger(trigger):

    if isinstance(trigger, six.string_types):
        return get_rules_with_trigger_ref(trigger_ref=trigger)

    if isinstance(trigger, dict):
        trigger_ref = trigger.get("ref", None)
        if trigger_ref:
            return get_rules_with_trigger_ref(trigger_ref=trigger_ref)
        else:
            raise ValueError("Trigger dict %s is missing ``ref``." % trigger)

    raise ValueError(
        "Unknown type %s for trigger. Cannot do rule lookups." % type(trigger)
    )


def get_rules_with_trigger_ref(trigger_ref=None, enabled=True):
    """
    Get rules in DB corresponding to given trigger_ref as a string reference.

    :param trigger_ref: Reference to trigger.
    :type trigger_ref: ``str``

    :rtype: ``list`` of ``RuleDB``
    """

    if not trigger_ref:
        return None

    LOG.debug("Querying rules with trigger %s", trigger_ref)
    return Rule.query(trigger=trigger_ref, enabled=enabled)
