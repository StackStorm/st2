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
from st2common import transport
from st2common.models.db.trigger import triggertype_access, trigger_access, triggerinstance_access
from st2common.persistence.base import (Access, ContentPackResource)
from st2common.transport import utils as transport_utils

LOG = logging.getLogger(__name__)


class TriggerType(ContentPackResource):
    impl = triggertype_access

    @classmethod
    def _get_impl(cls):
        return cls.impl


class Trigger(ContentPackResource):
    impl = trigger_access
    publisher = None

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_publisher(cls):
        if not cls.publisher:
            cls.publisher = transport.reactor.TriggerCUDPublisher(
                urls=transport_utils.get_messaging_urls())
        return cls.publisher

    @classmethod
    def delete_if_unreferenced(cls, model_object, publish=True, dispatch_trigger=True):
        # Found in the innards of mongoengine
        delete_query = model_object._object_key
        delete_query['lte__ref_count'] = 0
        cls._get_impl().delete_by_query(**delete_query)
        # Publish internal event on the message bus
        if publish:
            try:
                cls.publish_delete(model_object)
            except Exception:
                LOG.exception('Publish failed.')

        # Dispatch trigger
        if dispatch_trigger:
            try:
                cls.dispatch_delete_trigger(model_object)
            except Exception:
                LOG.exception('Trigger dispatch failed.')

        return model_object


class TriggerInstance(Access):
    impl = triggerinstance_access

    @classmethod
    def _get_impl(cls):
        return cls.impl
