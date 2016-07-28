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
import pecan
from pecan import abort
from six.moves import http_client

from st2api.controllers import resource
from st2common import log as logging
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.models.api.base import jsexpose
from st2common.models.api.policy import PolicyTypeAPI, PolicyAPI
from st2common.models.db.policy import PolicyTypeReference
from st2common.models.system.common import InvalidReferenceError
from st2common.persistence.policy import PolicyType, Policy
from st2common.validators.api.misc import validate_not_part_of_system_pack
from st2common.exceptions.db import StackStormDBObjectNotFoundError


LOG = logging.getLogger(__name__)


class PolicyTypeController(resource.ResourceController):
    model = PolicyTypeAPI
    access = PolicyType

    supported_filters = {
        'resource_type': 'resource_type'
    }

    query_options = {
        'sort': ['resource_type', 'name']
    }

    include_reference = False

    @jsexpose(arg_types=[str])
    def get_one(self, ref_or_id):
        return self._get_one(ref_or_id)

    @jsexpose()
    def get_all(self, **kwargs):
        return self._get_all(**kwargs)

    def _get_one(self, ref_or_id):
        LOG.info('GET %s with ref_or_id=%s', pecan.request.path, ref_or_id)

        instance = self._get_by_ref_or_id(ref_or_id=ref_or_id)
        result = self.model.from_model(instance)

        if result and self.include_reference:
            resource_type = getattr(result, 'resource_type', None)
            name = getattr(result, 'name', None)
            result.ref = PolicyTypeReference(resource_type=resource_type, name=name).ref

        LOG.debug('GET %s with ref_or_id=%s, client_result=%s',
                  pecan.request.path, ref_or_id, result)

        return result

    def _get_all(self, **kwargs):
        result = super(PolicyTypeController, self)._get_all(**kwargs)

        if self.include_reference:
            for item in result:
                resource_type = getattr(item, 'resource_type', None)
                name = getattr(item, 'name', None)
                item.ref = PolicyTypeReference(resource_type=resource_type, name=name).ref

        return result

    def _get_by_ref_or_id(self, ref_or_id):
        if PolicyTypeReference.is_reference(ref_or_id):
            resource_db = self._get_by_ref(resource_ref=ref_or_id)
        else:
            resource_db = self._get_by_id(resource_id=ref_or_id)

        if not resource_db:
            msg = 'PolicyType with a reference of id "%s" not found.' % (ref_or_id)
            raise StackStormDBObjectNotFoundError(msg)

        return resource_db

    def _get_by_id(self, resource_id):
        try:
            resource_db = self.access.get_by_id(resource_id)
        except Exception:
            resource_db = None

        return resource_db

    def _get_by_ref(self, resource_ref):
        try:
            ref = PolicyTypeReference.from_string_reference(ref=resource_ref)
        except Exception:
            return None

        resource_db = self.access.query(name=ref.name, resource_type=ref.resource_type).first()
        return resource_db

    def _get_filters(self, **kwargs):
        filters = copy.deepcopy(kwargs)
        ref = filters.get('ref', None)

        if ref:
            try:
                ref_obj = PolicyTypeReference.from_string_reference(ref=ref)
            except InvalidReferenceError:
                raise

            filters['name'] = ref_obj.name
            filters['resource_type'] = ref_obj.resource_type
            del filters['ref']

        return filters


class PolicyController(resource.ContentPackResourceController):
    model = PolicyAPI
    access = Policy

    supported_filters = {
        'pack': 'pack',
        'resource_ref': 'resource_ref',
        'policy_type': 'policy_type'
    }

    query_options = {
        'sort': ['pack', 'name']
    }

    @jsexpose(body_cls=PolicyAPI, status_code=http_client.CREATED)
    def post(self, instance):
        """
            Create a new policy.
            Handles requests:
                POST /policies/
        """
        op = 'POST /policies/'

        db_model = self.model.to_model(instance)
        LOG.debug('%s verified object: %s', op, db_model)

        db_model = self.access.add_or_update(db_model)

        LOG.debug('%s created object: %s', op, db_model)
        LOG.audit('Policy created. Policy.id=%s' % (db_model.id), extra={'policy_db': db_model})

        return self.model.from_model(db_model)

    @jsexpose(arg_types=[str], body_cls=PolicyAPI)
    def put(self, instance, ref_or_id):
        op = 'PUT /policies/%s/' % ref_or_id

        db_model = self._get_by_ref_or_id(ref_or_id=ref_or_id)
        LOG.debug('%s found object: %s', op, db_model)
        db_model_id = db_model.id

        try:
            validate_not_part_of_system_pack(db_model)
        except ValueValidationException as e:
            LOG.exception('%s unable to update object from system pack.', op)
            abort(http_client.BAD_REQUEST, str(e))

        if not getattr(instance, 'pack', None):
            instance.pack = db_model.pack

        try:
            db_model = self.model.to_model(instance)
            db_model.id = db_model_id
            db_model = self.access.add_or_update(db_model)
        except (ValidationError, ValueError) as e:
            LOG.exception('%s unable to update object: %s', op, db_model)
            abort(http_client.BAD_REQUEST, str(e))
            return

        LOG.debug('%s updated object: %s', op, db_model)
        LOG.audit('Policy updated. Policy.id=%s' % (db_model.id), extra={'policy_db': db_model})

        return self.model.from_model(db_model)

    @jsexpose(arg_types=[str], status_code=http_client.NO_CONTENT)
    def delete(self, ref_or_id):
        """
            Delete a policy.
            Handles requests:
                POST /policies/1?_method=delete
                DELETE /policies/1
                DELETE /policies/mypack.mypolicy
        """
        op = 'DELETE /policies/%s/' % ref_or_id

        db_model = self._get_by_ref_or_id(ref_or_id=ref_or_id)
        LOG.debug('%s found object: %s', op, db_model)

        try:
            validate_not_part_of_system_pack(db_model)
        except ValueValidationException as e:
            LOG.exception('%s unable to delete object from system pack.', op)
            abort(http_client.BAD_REQUEST, str(e))

        try:
            self.access.delete(db_model)
        except Exception as e:
            LOG.exception('%s unable to delete object: %s', op, db_model)
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))
            return

        LOG.debug('%s deleted object: %s', op, db_model)
        LOG.audit('Policy deleted. Policy.id=%s' % (db_model.id), extra={'policy_db': db_model})

        return None
