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

from st2common import log as logging
from st2common import transport
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.db.trigger import (
    triggertype_access,
    trigger_access,
    triggerinstance_access,
)
from st2common.persistence.base import Access, ContentPackResource

__all__ = ["TriggerType", "Trigger", "TriggerInstance"]

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
            cls.publisher = transport.reactor.TriggerCUDPublisher()
        return cls.publisher

    @classmethod
    def delete_if_unreferenced(cls, model_object, publish=True, dispatch_trigger=True):
        # Found in the innards of mongoengine.
        # e.g. {'pk': ObjectId('5609e91832ed356d04a93cc0')}
        delete_query = model_object._object_key
        delete_query["ref_count__lte"] = 0
        cls._get_impl().delete_by_query(**delete_query)

        # Since delete_by_query cannot tell if teh delete actually happened check with a get call
        # if the trigger was deleted. Unfortuantely, this opens up to races on delete.
        confirmed_delete = False
        try:
            cls.get_by_id(model_object.id)
        except (StackStormDBObjectNotFoundError, ValueError):
            confirmed_delete = True

        # Publish internal event on the message bus
        if confirmed_delete and publish:
            try:
                cls.publish_delete(model_object)
            except Exception:
                LOG.exception("Publish failed.")

        # Dispatch trigger
        if confirmed_delete and dispatch_trigger:
            try:
                cls.dispatch_delete_trigger(model_object)
            except Exception:
                LOG.exception("Trigger dispatch failed.")

        return model_object


class TriggerInstance(Access):
    impl = triggerinstance_access

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def delete_by_query(cls, *args, **query):
        return cls._get_impl().delete_by_query(*args, **query)
