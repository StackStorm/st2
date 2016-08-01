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

import copy

from mongoengine import ValidationError
from pecan import abort
from pecan.rest import RestController
import six

from st2api.controllers import resource
from st2common import log as logging
from st2common.models.api.trigger import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI
from st2common.models.api.base import jsexpose
from st2common.models.system.common import ResourceReference
from st2common.persistence.trigger import TriggerType, Trigger, TriggerInstance
from st2common.services import triggers as TriggerService
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.exceptions.db import StackStormDBObjectConflictError
from st2common.transport.reactor import TriggerDispatcher
from st2common.util import isotime
from st2common.validators.api.misc import validate_not_part_of_system_pack

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class TriggerTypeController(resource.ContentPackResourceController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of TriggerTypes in the system.
    """
    model = TriggerTypeAPI
    access = TriggerType
    supported_filters = {
        'name': 'name',
        'pack': 'pack'
    }

    options = {
        'sort': ['pack', 'name']
    }

    include_reference = True

    @jsexpose(body_cls=TriggerTypeAPI, status_code=http_client.CREATED)
    def post(self, triggertype):
        """
            Create a new triggertype.

            Handles requests:
                POST /triggertypes/
        """

        try:
            triggertype_db = TriggerTypeAPI.to_model(triggertype)
            triggertype_db = TriggerType.add_or_update(triggertype_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for triggertype data=%s.', triggertype)
            abort(http_client.BAD_REQUEST, str(e))
            return
        else:
            extra = {'triggertype_db': triggertype_db}
            LOG.audit('TriggerType created. TriggerType.id=%s' % (triggertype_db.id), extra=extra)
            if not triggertype_db.parameters_schema:
                TriggerTypeController._create_shadow_trigger(triggertype_db)

        triggertype_api = TriggerTypeAPI.from_model(triggertype_db)

        return triggertype_api

    @jsexpose(arg_types=[str], body_cls=TriggerTypeAPI)
    def put(self, triggertype, triggertype_ref_or_id):
        triggertype_db = self._get_by_ref_or_id(ref_or_id=triggertype_ref_or_id)
        triggertype_id = triggertype_db.id

        try:
            validate_not_part_of_system_pack(triggertype_db)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, str(e))

        try:
            triggertype_db = TriggerTypeAPI.to_model(triggertype)
            if triggertype.id is not None and len(triggertype.id) > 0 and \
               triggertype.id != triggertype_id:
                LOG.warning('Discarding mismatched id=%s found in payload and using uri_id=%s.',
                            triggertype.id, triggertype_id)
            triggertype_db.id = triggertype_id
            old_triggertype_db = triggertype_db
            triggertype_db = TriggerType.add_or_update(triggertype_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for triggertype data=%s', triggertype)
            abort(http_client.BAD_REQUEST, str(e))
            return

        extra = {'old_triggertype_db': old_triggertype_db, 'new_triggertype_db': triggertype_db}
        LOG.audit('TriggerType updated. TriggerType.id=%s' % (triggertype_db.id), extra=extra)

        triggertype_api = TriggerTypeAPI.from_model(triggertype_db)
        return triggertype_api

    @jsexpose(arg_types=[str], status_code=http_client.NO_CONTENT)
    def delete(self, triggertype_ref_or_id):
        """
            Delete a triggertype.

            Handles requests:
                DELETE /triggertypes/1
                DELETE /triggertypes/pack.name
        """
        LOG.info('DELETE /triggertypes/ with ref_or_id=%s',
                 triggertype_ref_or_id)

        triggertype_db = self._get_by_ref_or_id(ref_or_id=triggertype_ref_or_id)
        triggertype_id = triggertype_db.id

        try:
            validate_not_part_of_system_pack(triggertype_db)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, str(e))

        try:
            TriggerType.delete(triggertype_db)
        except Exception as e:
            LOG.exception('Database delete encountered exception during delete of id="%s". ',
                          triggertype_id)
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return
        else:
            extra = {'triggertype': triggertype_db}
            LOG.audit('TriggerType deleted. TriggerType.id=%s' % (triggertype_db.id), extra=extra)
            if not triggertype_db.parameters_schema:
                TriggerTypeController._delete_shadow_trigger(triggertype_db)

    @staticmethod
    def _create_shadow_trigger(triggertype_db):
        try:
            trigger_type_ref = triggertype_db.get_reference().ref
            trigger = {'name': triggertype_db.name,
                       'pack': triggertype_db.pack,
                       'type': trigger_type_ref,
                       'parameters': {}}
            trigger_db = TriggerService.create_or_update_trigger_db(trigger)

            extra = {'trigger_db': trigger_db}
            LOG.audit('Trigger created for parameter-less TriggerType. Trigger.id=%s' %
                      (trigger_db.id), extra=extra)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for trigger data=%s.', trigger)
            # Not aborting as this is convenience.
            return
        except StackStormDBObjectConflictError as e:
            LOG.warn('Trigger creation of "%s" failed with uniqueness conflict. Exception: %s',
                     trigger, str(e))
            # Not aborting as this is convenience.
            return

    @staticmethod
    def _delete_shadow_trigger(triggertype_db):
        # shadow Trigger's have the same name as the shadowed TriggerType.
        triggertype_ref = ResourceReference(name=triggertype_db.name, pack=triggertype_db.pack)
        trigger_db = TriggerService.get_trigger_db_by_ref(triggertype_ref.ref)
        if not trigger_db:
            LOG.warn('No shadow trigger found for %s. Will skip delete.', triggertype_db)
            return
        try:
            Trigger.delete(trigger_db)
        except Exception:
            LOG.exception('Database delete encountered exception during delete of id="%s". ',
                          trigger_db.id)

        extra = {'trigger_db': trigger_db}
        LOG.audit('Trigger deleted. Trigger.id=%s' % (trigger_db.id), extra=extra)


class TriggerController(RestController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of Triggers in the system.
    """
    @jsexpose(arg_types=[str])
    def get_one(self, trigger_id):

        """
            List trigger by id.

            Handle:
                GET /triggers/1
        """
        trigger_db = TriggerController.__get_by_id(trigger_id)
        trigger_api = TriggerAPI.from_model(trigger_db)
        return trigger_api

    @jsexpose(arg_types=[str])
    def get_all(self, **kw):
        """
            List all triggers.

            Handles requests:
                GET /triggers/
        """
        trigger_dbs = Trigger.get_all(**kw)
        trigger_apis = [TriggerAPI.from_model(trigger_db) for trigger_db in trigger_dbs]
        return trigger_apis

    @jsexpose(body_cls=TriggerAPI, status_code=http_client.CREATED)
    def post(self, trigger):
        """
            Create a new trigger.

            Handles requests:
                POST /triggers/
        """
        try:
            trigger_db = TriggerService.create_trigger_db(trigger)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for trigger data=%s.', trigger)
            abort(http_client.BAD_REQUEST, str(e))
            return

        extra = {'trigger': trigger_db}
        LOG.audit('Trigger created. Trigger.id=%s' % (trigger_db.id), extra=extra)
        trigger_api = TriggerAPI.from_model(trigger_db)

        return trigger_api

    @jsexpose(arg_types=[str], body_cls=TriggerAPI)
    def put(self, trigger, trigger_id):
        trigger_db = TriggerController.__get_by_id(trigger_id)
        try:
            if trigger.id is not None and trigger.id is not '' and trigger.id != trigger_id:
                LOG.warning('Discarding mismatched id=%s found in payload and using uri_id=%s.',
                            trigger.id, trigger_id)
            trigger_db = TriggerAPI.to_model(trigger)
            trigger_db.id = trigger_id
            trigger_db = Trigger.add_or_update(trigger_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Validation failed for trigger data=%s', trigger)
            abort(http_client.BAD_REQUEST, str(e))
            return

        extra = {'old_trigger_db': trigger, 'new_trigger_db': trigger_db}
        LOG.audit('Trigger updated. Trigger.id=%s' % (trigger.id), extra=extra)
        trigger_api = TriggerAPI.from_model(trigger_db)

        return trigger_api

    @jsexpose(arg_types=[str], status_code=http_client.NO_CONTENT)
    def delete(self, trigger_id):
        """
            Delete a trigger.

            Handles requests:
                DELETE /triggers/1
        """
        LOG.info('DELETE /triggers/ with id=%s', trigger_id)
        trigger_db = TriggerController.__get_by_id(trigger_id)
        try:
            Trigger.delete(trigger_db)
        except Exception as e:
            LOG.exception('Database delete encountered exception during delete of id="%s". ',
                          trigger_id)
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        extra = {'trigger_db': trigger_db}
        LOG.audit('Trigger deleted. Trigger.id=%s' % (trigger_db.id), extra=extra)

    @staticmethod
    def __get_by_id(trigger_id):
        try:
            return Trigger.get_by_id(trigger_id)
        except (ValueError, ValidationError):
            LOG.exception('Database lookup for id="%s" resulted in exception.', trigger_id)
            abort(http_client.NOT_FOUND)

    @staticmethod
    def __get_by_name(trigger_name):
        try:
            return [Trigger.get_by_name(trigger_name)]
        except ValueError as e:
            LOG.debug('Database lookup for name="%s" resulted in exception : %s.', trigger_name, e)
            return []


class TriggerInstanceControllerMixin(RestController):
    model = TriggerInstanceAPI
    access = TriggerInstance


class TriggerInstanceResendController(TriggerInstanceControllerMixin, resource.ResourceController):
    supported_filters = {}

    def __init__(self, *args, **kwargs):
        super(TriggerInstanceResendController, self).__init__(*args, **kwargs)
        self.trigger_dispatcher = TriggerDispatcher(LOG)

    class TriggerInstancePayload(object):
        def __init__(self, payload=None):
            self.payload = payload or {}

        def validate(self):
            if self.payload:
                assert isinstance(self.payload, dict)

            return True

    @jsexpose(status_code=http_client.OK)
    def post(self, trigger_instance_id):
        """
        Re-send the provided trigger instance optionally specifying override parameters.

        Handles requests:

            POST /triggerinstance/<id>/re_emit
            POST /triggerinstance/<id>/re_send
        """
        # Note: We only really need parameters here
        existing_trigger_instance = self._get_one(id=trigger_instance_id)

        new_payload = copy.deepcopy(existing_trigger_instance.payload)
        new_payload['__context'] = {
            'original_id': trigger_instance_id
        }

        try:
            self.trigger_dispatcher.dispatch(existing_trigger_instance.trigger,
                                             new_payload)
            return {
                'message': 'Trigger instance %s succesfully re-sent.' % trigger_instance_id,
                'payload': new_payload
            }
        except Exception as e:
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))


class TriggerInstanceController(TriggerInstanceControllerMixin, resource.ResourceController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of TriggerInstances in the system.
    """
    re_emit = TriggerInstanceResendController()

    supported_filters = {
        'trigger': 'trigger',
        'timestamp_gt': 'occurrence_time.gt',
        'timestamp_lt': 'occurrence_time.lt',
        'status': 'status'
    }

    filter_transform_functions = {
        'timestamp_gt': lambda value: isotime.parse(value=value),
        'timestamp_lt': lambda value: isotime.parse(value=value)
    }

    query_options = {
        'sort': ['-occurrence_time', 'trigger']
    }

    def __init__(self):
        super(TriggerInstanceController, self).__init__()

    @jsexpose(arg_types=[str])
    def get_one(self, instance_id):
        """
            List triggerinstance by instance_id.

            Handle:
                GET /triggerinstances/1
        """
        return self._get_one(instance_id)

    @jsexpose()
    def get_all(self, **kw):
        """
            List all triggerinstances.

            Handles requests:
                GET /triggerinstances/
        """
        trigger_instances = self._get_trigger_instances(**kw)
        return trigger_instances

    def _get_trigger_instances(self, **kw):
        kw['limit'] = int(kw.get('limit', self.default_limit))

        LOG.debug('Retrieving all trigger instances with filters=%s', kw)
        return super(TriggerInstanceController, self)._get_all(**kw)
