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

# pylint: disable=no-member

import abc
import copy

from mongoengine import ValidationError
import pecan
from pecan import rest
import six
from six.moves import http_client

from st2common.models.api.base import jsexpose
from st2common import log as logging
from st2common.models.system.common import InvalidResourceReferenceError
from st2common.models.system.common import ResourceReference


LOG = logging.getLogger(__name__)

RESERVED_QUERY_PARAMS = {
    'id': 'id',
    'name': 'name',
    'sort': 'order_by'
}


@six.add_metaclass(abc.ABCMeta)
class ResourceController(rest.RestController):
    model = abc.abstractproperty
    access = abc.abstractproperty
    supported_filters = abc.abstractproperty

    # Maximum value of limit which can be specified by user
    max_limit = 100

    query_options = {
        'sort': []
    }

    # A list of optional transformation functions for user provided filter values
    filter_transform_functions = {}

    def __init__(self):
        self.supported_filters = copy.deepcopy(self.__class__.supported_filters)
        self.supported_filters.update(RESERVED_QUERY_PARAMS)

    @jsexpose()
    def get_all(self, **kwargs):
        return self._get_all(**kwargs)

    @jsexpose(arg_types=[str])
    def get_one(self, id):
        return self._get_one(id)

    def _get_all(self, exclude_fields=None, **kwargs):
        """
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        """
        exclude_fields = exclude_fields or []

        # TODO: Why do we use comma delimited string, user can just specify
        # multiple values using ?sort=foo&sort=bar and we get a list back
        sort = kwargs.get('sort').split(',') if kwargs.get('sort') else []

        db_sort_values = []
        for sort_key in sort:
            if sort_key.startswith('-'):
                direction = '-'
                sort_key = sort_key[1:]
            elif sort_key.startswith('+'):
                direction = '+'
                sort_key = sort_key[1:]
            else:
                direction = ''

            if sort_key not in self.supported_filters:
                # Skip unsupported sort key
                continue

            sort_value = direction + self.supported_filters[sort_key]
            db_sort_values.append(sort_value)

        default_sort_values = copy.copy(self.query_options.get('sort'))
        kwargs['sort'] = db_sort_values if db_sort_values else default_sort_values

        # TODO: To protect us from DoS, we need to make max_limit mandatory
        offset = int(kwargs.pop('offset', 0))
        limit = kwargs.pop('limit', None)

        if limit and int(limit) > self.max_limit:
            limit = self.max_limit
        eop = offset + int(limit) if limit else None

        filters = {}

        for k, v in six.iteritems(self.supported_filters):
            filter_value = kwargs.get(k, None)

            if not filter_value:
                continue

            value_transform_function = self.filter_transform_functions.get(k, None)
            value_transform_function = value_transform_function or (lambda value: value)
            filter_value = value_transform_function(value=filter_value)

            filters['__'.join(v.split('.'))] = filter_value

        LOG.info('GET all %s with filters=%s', pecan.request.path, filters)

        instances = self.access.query(exclude_fields=exclude_fields, **filters)

        if limit:
            pecan.response.headers['X-Limit'] = str(limit)
        pecan.response.headers['X-Total-Count'] = str(instances.count())

        return [self.model.from_model(instance) for instance in instances[offset:eop]]

    def _get_one(self, id, exclude_fields=None):
        """
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        """

        LOG.info('GET %s with id=%s', pecan.request.path, id)

        instance = None

        try:
            instance = self.access.get(id=id, exclude_fields=exclude_fields)
        except ValidationError:
            instance = None  # Someone supplied a mongo non-comformant id.

        if not instance:
            msg = 'Unable to identify resource with id "%s".' % id
            pecan.abort(http_client.NOT_FOUND, msg)

        result = self.model.from_model(instance)
        LOG.debug('GET %s with id=%s, client_result=%s', pecan.request.path, id, result)

        return result

    def _get_by_name_or_id(self, name_or_id):
        """
        Retrieve resource object by an id of a name.
        """
        resource_db = self._get_by_id(resource_id=name_or_id)

        if not resource_db:
            # Try name
            resource_db = self._get_by_name(resource_name=name_or_id)

        if not resource_db:
            msg = 'Resource with a name of id "%s" not found' % (name_or_id)
            raise Exception(msg)

        return resource_db

    def _get_by_id(self, resource_id):
        try:
            resource_db = self.access.get_by_id(resource_id)
        except Exception:
            resource_db = None

        return resource_db

    def _get_by_name(self, resource_name):
        try:
            resource_db = self.access.get_by_name(resource_name)
        except Exception:
            resource_db = None

        return resource_db


class ContentPackResourceController(ResourceController):
    include_reference = False

    @jsexpose(arg_types=[str])
    def get_one(self, ref_or_id):
        return self._get_one(ref_or_id)

    @jsexpose()
    def get_all(self, **kwargs):
        return self._get_all(**kwargs)

    def _get_one(self, ref_or_id):
        LOG.info('GET %s with ref_or_id=%s', pecan.request.path, ref_or_id)

        try:
            instance = self._get_by_ref_or_id(ref_or_id=ref_or_id)
        except Exception as e:
            LOG.exception(e.message)
            pecan.abort(http_client.NOT_FOUND, e.message)
            return

        result = self.model.from_model(instance)
        if result and self.include_reference:
                pack = getattr(result, 'pack', None)
                name = getattr(result, 'name', None)
                result.ref = ResourceReference(pack=pack, name=name).ref

        LOG.debug('GET %s with ref_or_id=%s, client_result=%s',
                  pecan.request.path, ref_or_id, result)

        return result

    def _get_all(self, **kwargs):
        result = super(ContentPackResourceController, self)._get_all(**kwargs)

        if self.include_reference:
            for item in result:
                pack = getattr(item, 'pack', None)
                name = getattr(item, 'name', None)
                item.ref = ResourceReference(pack=pack, name=name).ref

        return result

    def _get_by_ref_or_id(self, ref_or_id):
        """
        Retrieve resource object by an id of a reference.
        """

        if ResourceReference.is_resource_reference(ref_or_id):
            # references always contain a dot and id's can't contain it
            is_reference = True
        else:
            is_reference = False

        if is_reference:
            resource_db = self._get_by_ref(resource_ref=ref_or_id)
        else:
            resource_db = self._get_by_id(resource_id=ref_or_id)

        if not resource_db:
            msg = 'Resource with a reference of id "%s" not found' % (ref_or_id)
            raise Exception(msg)

        return resource_db

    def _get_by_id(self, resource_id):
        try:
            resource_db = self.access.get_by_id(resource_id)
        except Exception:
            resource_db = None

        return resource_db

    def _get_by_ref(self, resource_ref):
        try:
            ref = ResourceReference.from_string_reference(ref=resource_ref)
        except Exception:
            return None

        resource_db = self.access.query(name=ref.name, pack=ref.pack).first()
        return resource_db

    def _get_filters(self, **kwargs):
        filters = copy.deepcopy(kwargs)
        ref = filters.get('ref', None)

        if ref:
            try:
                ref_obj = ResourceReference.from_string_reference(ref=ref)
            except InvalidResourceReferenceError:
                raise

            filters['name'] = ref_obj.name
            filters['pack'] = ref_obj.pack
            del filters['ref']

        return filters
