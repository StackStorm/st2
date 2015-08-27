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

from st2common.models.db.trace import trace_access
from st2common.persistence.base import Access


class Trace(Access):
    impl = trace_access

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def push_components(cls, instance, action_executions=None, rules=None, trigger_instances=None):
        update_kwargs = {}
        if action_executions:
            update_kwargs['push_all__action_executions'] = action_executions
        if rules:
            update_kwargs['push_all__rules'] = rules
        if trigger_instances:
            update_kwargs['push_all__trigger_instances'] = trigger_instances
        if update_kwargs:
            return cls.update(instance, **update_kwargs)
        return instance

    @classmethod
    def push_action_execution(cls, instance, action_execution):
        return cls.update(instance, push__action_executions=action_execution)

    @classmethod
    def push_rule(cls, instance, rule):
        return cls.update(instance, push__rules=rule)

    @classmethod
    def push_trigger_instance(cls, instance, trigger_instance):
        return cls.update(instance, push__trigger_instances=trigger_instance)
