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

from oslo.config import cfg
from st2common import transport
from st2common.persistence import Access
from st2common.models.db.reactor import sensor_type_access
from st2common.models.db.reactor import triggertype_access, trigger_access, triggerinstance_access,\
    rule_access
from st2common.models.system.common import ResourceReference


class ContentPackResourceMixin():
    @classmethod
    def get_by_ref(cls, ref):
        if not ref:
            return None

        ref_obj = ResourceReference.from_string_reference(ref=ref)
        result = cls.query(name=ref_obj.name,
                           pack=ref_obj.pack).first()
        return result


class SensorType(Access, ContentPackResourceMixin):
    impl = sensor_type_access

    @classmethod
    def _get_impl(kls):
        return kls.impl


class TriggerType(Access, ContentPackResourceMixin):
    impl = triggertype_access

    @classmethod
    def _get_impl(kls):
        return kls.impl


class Trigger(Access, ContentPackResourceMixin):
    impl = trigger_access
    publisher = None

    @classmethod
    def _get_impl(kls):
        return kls.impl

    @classmethod
    def _get_publisher(kls):
        if not kls.publisher:
            kls.publisher = transport.reactor.TriggerCUDPublisher(cfg.CONF.messaging.url)
        return kls.publisher


class TriggerInstance(Access):
    impl = triggerinstance_access

    @classmethod
    def _get_impl(kls):
        return kls.impl


class Rule(Access):
    impl = rule_access

    @classmethod
    def _get_impl(kls):
        return kls.impl
