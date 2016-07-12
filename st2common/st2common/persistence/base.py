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

import abc

import six
from mongoengine import NotUniqueError

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectConflictError
from st2common.models.system.common import ResourceReference
from st2common.transport.reactor import TriggerDispatcher


__all__ = [
    'Access',

    'ContentPackResource',
    'StatusBasedResource'
]

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class Access(object):
    impl = None
    publisher = None
    dispatcher = None

    # ModelAPI class for this resource
    api_model_cls = None

    # A list of operations for which we should dispatch a trigger
    dispatch_trigger_for_operations = []

    # Maps model operation name (e.g. create, update, delete) to the trigger reference which is
    # used when dispatching a trigger
    operation_to_trigger_ref_map = {}

    @classmethod
    @abc.abstractmethod
    def _get_impl(cls):
        pass

    @classmethod
    @abc.abstractmethod
    def _get_publisher(cls):
        return None

    @classmethod
    def _get_dispatcher(cls):
        """
        Return a dispatcher class which is used for dispatching triggers.
        """
        if not cls.dispatcher:
            cls.dispatcher = TriggerDispatcher(LOG)

        return cls.dispatcher

    @classmethod
    @abc.abstractmethod
    def _get_by_object(cls, object):
        return None

    @classmethod
    def get_by_name(cls, value):
        return cls._get_impl().get_by_name(value)

    @classmethod
    def get_by_id(cls, value):
        return cls._get_impl().get_by_id(value)

    @classmethod
    def get_by_uid(cls, value):
        return cls._get_impl().get_by_uid(value)

    @classmethod
    def get_by_ref(cls, value):
        return cls._get_impl().get_by_ref(value)

    @classmethod
    def get_by_pack(cls, value):
        return cls._get_impl().get_by_pack(value)

    @classmethod
    def get(cls, *args, **kwargs):
        return cls._get_impl().get(*args, **kwargs)

    @classmethod
    def get_all(cls, *args, **kwargs):
        return cls._get_impl().get_all(*args, **kwargs)

    @classmethod
    def count(cls, *args, **kwargs):
        return cls._get_impl().count(*args, **kwargs)

    @classmethod
    def query(cls, *args, **kwargs):
        return cls._get_impl().query(*args, **kwargs)

    @classmethod
    def distinct(cls, *args, **kwargs):
        return cls._get_impl().distinct(*args, **kwargs)

    @classmethod
    def aggregate(cls, *args, **kwargs):
        return cls._get_impl().aggregate(*args, **kwargs)

    @classmethod
    def insert(cls, model_object, publish=True, dispatch_trigger=True,
               log_not_unique_error_as_debug=False):
        if model_object.id:
            raise ValueError('id for object %s was unexpected.' % model_object)
        try:
            model_object = cls._get_impl().insert(model_object)
        except NotUniqueError as e:
            if log_not_unique_error_as_debug:
                LOG.debug('Conflict while trying to save in DB: %s.', str(e))
            else:
                LOG.exception('Conflict while trying to save in DB.')
            # On a conflict determine the conflicting object and return its id in
            # the raised exception.
            conflict_object = cls._get_by_object(model_object)
            conflict_id = str(conflict_object.id) if conflict_object else None
            message = str(e)
            raise StackStormDBObjectConflictError(message=message, conflict_id=conflict_id,
                                                  model_object=model_object)

        # Publish internal event on the message bus
        if publish:
            try:
                cls.publish_create(model_object)
            except:
                LOG.exception('Publish failed.')

        # Dispatch trigger
        if dispatch_trigger:
            try:
                cls.dispatch_create_trigger(model_object)
            except:
                LOG.exception('Trigger dispatch failed.')

        return model_object

    @classmethod
    def add_or_update(cls, model_object, publish=True, dispatch_trigger=True,
                      log_not_unique_error_as_debug=False):
        pre_persist_id = model_object.id
        try:
            model_object = cls._get_impl().add_or_update(model_object)
        except NotUniqueError as e:
            if log_not_unique_error_as_debug:
                LOG.debug('Conflict while trying to save in DB: %s.', str(e))
            else:
                LOG.exception('Conflict while trying to save in DB.')
            # On a conflict determine the conflicting object and return its id in
            # the raised exception.
            conflict_object = cls._get_by_object(model_object)
            conflict_id = str(conflict_object.id) if conflict_object else None
            message = str(e)
            raise StackStormDBObjectConflictError(message=message, conflict_id=conflict_id,
                                                  model_object=model_object)

        is_update = str(pre_persist_id) == str(model_object.id)

        # Publish internal event on the message bus
        if publish:
            try:
                if is_update:
                    cls.publish_update(model_object)
                else:
                    cls.publish_create(model_object)
            except:
                LOG.exception('Publish failed.')

        # Dispatch trigger
        if dispatch_trigger:
            try:
                if is_update:
                    cls.dispatch_update_trigger(model_object)
                else:
                    cls.dispatch_create_trigger(model_object)
            except:
                LOG.exception('Trigger dispatch failed.')

        return model_object

    @classmethod
    def update(cls, model_object, publish=True, dispatch_trigger=True, **kwargs):
        """
        Use this method when -
        * upsert=False is desired
        * special operators like push, push_all are to be used.
        """
        cls._get_impl().update(model_object, **kwargs)
        # update does not return the object but a flag; likely success/fail but docs
        # are not very good on this one so ignoring. Explicitly get the object from
        # DB abd return.
        model_object = cls.get_by_id(model_object.id)

        # Publish internal event on the message bus
        if publish:
            try:
                cls.publish_update(model_object)
            except:
                LOG.exception('Publish failed.')

        # Dispatch trigger
        if dispatch_trigger:
            try:
                cls.dispatch_update_trigger(model_object)
            except:
                LOG.exception('Trigger dispatch failed.')

        return model_object

    @classmethod
    def delete(cls, model_object, publish=True, dispatch_trigger=True):
        persisted_object = cls._get_impl().delete(model_object)

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

        return persisted_object

    ####################################################
    # Internal event bus message publish related methods
    ####################################################

    @classmethod
    def publish_create(cls, model_object):
        publisher = cls._get_publisher()
        if publisher:
            publisher.publish_create(model_object)

    @classmethod
    def publish_update(cls, model_object):
        publisher = cls._get_publisher()
        if publisher:
            publisher.publish_update(model_object)

    @classmethod
    def publish_delete(cls, model_object):
        publisher = cls._get_publisher()
        if publisher:
            publisher.publish_delete(model_object)

    ############################################
    # Internal trigger dispatch related methods
    ###########################################

    @classmethod
    def dispatch_create_trigger(cls, model_object):
        """
        Dispatch a resource-specific trigger which indicates a new resource has been created.
        """
        return cls._dispatch_operation_trigger(operation='create', model_object=model_object)

    @classmethod
    def dispatch_update_trigger(cls, model_object):
        """
        Dispatch a resource-specific trigger which indicates an existing resource has been updated.
        """
        return cls._dispatch_operation_trigger(operation='update', model_object=model_object)

    @classmethod
    def dispatch_delete_trigger(cls, model_object):
        """
        Dispatch a resource-specific trigger which indicates an existing resource has been
        deleted.
        """
        return cls._dispatch_operation_trigger(operation='delete', model_object=model_object)

    @classmethod
    def _get_trigger_ref_for_operation(cls, operation):
        trigger_ref = cls.operation_to_trigger_ref_map.get(operation, None)

        if not trigger_ref:
            raise ValueError('Trigger ref not specified for operation: %s' % (operation))

        return trigger_ref

    @classmethod
    def _dispatch_operation_trigger(cls, operation, model_object):
        if operation not in cls.dispatch_trigger_for_operations:
            return

        trigger = cls._get_trigger_ref_for_operation(operation=operation)

        object_payload = cls.api_model_cls.from_model(model_object, mask_secrets=True).__json__()
        payload = {
            'object': object_payload
        }
        return cls._dispatch_trigger(operation=operation, trigger=trigger, payload=payload)

    @classmethod
    def _dispatch_trigger(cls, operation, trigger, payload):
        if operation not in cls.dispatch_trigger_for_operations:
            return

        dispatcher = cls._get_dispatcher()
        return dispatcher.dispatch(trigger=trigger, payload=payload)


class ContentPackResource(Access):

    @classmethod
    def get_by_ref(cls, ref):
        if not ref:
            return None

        ref_obj = ResourceReference.from_string_reference(ref=ref)
        result = cls.query(name=ref_obj.name,
                           pack=ref_obj.pack).first()
        return result

    @classmethod
    def _get_by_object(cls, object):
        # For an object with a resourcepack pack.name is unique.
        name = getattr(object, 'name', '')
        pack = getattr(object, 'pack', '')
        return cls.get_by_ref(ResourceReference.to_string_reference(pack=pack, name=name))


class StatusBasedResource(Access):
    """Persistence layer for models that needs to publish status to the message queue."""

    @classmethod
    def publish_status(cls, model_object):
        """Publish the object status to the message queue.

        Publish the instance of the model as payload with the status
        as routing key to the message queue via the StatePublisher.

        :param model_object: An instance of the model.
        :type model_object: ``object``
        """
        publisher = cls._get_publisher()
        if publisher:
            publisher.publish_state(model_object, getattr(model_object, 'status', None))
