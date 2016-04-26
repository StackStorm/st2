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

import logging

from st2client.models import core


LOG = logging.getLogger(__name__)


class Sensor(core.Resource):
    _plural = 'Sensortypes'
    _repr_attributes = ['name', 'pack']


class TriggerType(core.Resource):
    _alias = 'Trigger'
    _display_name = 'Trigger'
    _plural = 'Triggertypes'
    _plural_display_name = 'Triggers'
    _repr_attributes = ['name', 'pack']


class TriggerInstance(core.Resource):
    _alias = 'Trigger-Instance'
    _display_name = 'TriggerInstance'
    _plural = 'Triggerinstances'
    _plural_display_name = 'TriggerInstances'
    _repr_attributes = ['id', 'trigger', 'occurrence_time', 'payload', 'status']


class Trigger(core.Resource):
    _alias = 'TriggerSpecification'
    _display_name = 'Trigger Specification'
    _plural = 'Triggers'
    _plural_display_name = 'Trigger Specifications'
    _repr_attributes = ['name', 'pack']


class Rule(core.Resource):
    _alias = 'Rule'
    _plural = 'Rules'
    _repr_attributes = ['name', 'pack', 'trigger', 'criteria', 'enabled']


class RuleEnforcement(core.Resource):
    _alias = 'Rule-Enforcement'
    _plural = 'RuleEnforcements'
    _display_name = 'Rule Enforcement'
    _plural_display_name = 'Rule Enforcements'
    _repr_attributes = ['id', 'trigger_instance_id', 'execution_id', 'rule.ref', 'enforced_at']
