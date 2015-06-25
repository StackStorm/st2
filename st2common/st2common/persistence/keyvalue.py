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

from st2common.persistence.base import Access
from st2common.models.db import keyvalue
from st2common.models.api.keyvalue import KeyValuePairAPI
from st2common.constants.triggers import KEY_VALUE_PAIR_UPDATE_TRIGGER
from st2common.constants.triggers import KEY_VALUE_PAIR_VALUE_CHANGE_TRIGGER
from st2common.constants.triggers import KEY_VALUE_PAIR_DELETE_TRIGGER


class KeyValuePair(Access):
    impl = keyvalue.keyvaluepair_access
    publisher = None

    api_model_cls = KeyValuePairAPI
    dispatch_trigger_for_operations = ['create', 'update', 'value_change', 'delete']
    operation_to_trigger_ref_map = {
        'create': KEY_VALUE_PAIR_UPDATE_TRIGGER['name'],
        'update': KEY_VALUE_PAIR_UPDATE_TRIGGER['name'],
        'value_change': KEY_VALUE_PAIR_VALUE_CHANGE_TRIGGER['name'],
        'delete': KEY_VALUE_PAIR_DELETE_TRIGGER['name'],
    }

    @classmethod
    def add_or_update(cls, model_object, publish=True, dispatch_trigger=True):
        """
        Note: We override add_or_update because we also want to publish high level "value_change"
        event for this resource.
        """
        if model_object.id:
            existing_model_object = cls.get_by_id(value=model_object.id)
        else:
            # Not an update
            existing_model_object = None

        model_object = super(KeyValuePair, cls).add_or_update(model_object=model_object,
                                                              publish=publish,
                                                              dispatch_trigger=dispatch_trigger)

        # Dispatch a value_change event which is specific to this resource
        if existing_model_object and existing_model_object.value != model_object.value:
            cls.dispatch_value_change_trigger(old_model_object=existing_model_object,
                                              new_model_object=model_object)

        return model_object

    @classmethod
    def dispatch_value_change_trigger(cls, old_model_object, new_model_object):
        operation = 'value_change'
        trigger = cls._get_trigger_ref_for_operation(operation=operation)

        old_object_payload = cls.api_model_cls.from_model(old_model_object,
                                                          mask_secrets=True).__json__()
        new_object_payload = cls.api_model_cls.from_model(new_model_object,
                                                          mask_secrets=True).__json__()
        payload = {
            'old_object': old_object_payload,
            'new_object': new_object_payload
        }

        return cls._dispatch_trigger(operation=operation, trigger=trigger, payload=payload)

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_by_object(cls, object):
        # For KeyValuePair name is unique.
        name = getattr(object, 'name', '')
        return cls.get_by_name(name)
