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

from oslo_config import cfg
from mongoengine import ValidationError
import pecan
from pecan import rest
import six
from six.moves import http_client

from st2common.models.api.base import jsexpose
from st2common import log as logging
from st2common.models.system.common import InvalidResourceReferenceError
from st2common.models.system.common import ResourceReference
from st2common.exceptions.db import StackStormDBObjectNotFoundError

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

    # Default kwargs passed to "APIClass.from_model" method
    from_model_kwargs = {}

    # Maximum value of limit which can be specified by user
    max_limit = cfg.CONF.api.max_page_size

    # Default number of items returned per page if no limit is explicitly provided
    default_limit = 100

    query_options = {
        'sort': []
    }

    # A list of optional transformation functions for user provided filter values
    filter_transform_functions = {}

    # A list of attributes which can be specified using ?exclude_attributes filter
    valid_exclude_attributes = []

    # Method responsible for retrieving an instance of the corresponding model DB object
    # Note: This method should throw StackStormDBObjectNotFoundError if the corresponding DB
    # object doesn't exist
    get_one_db_method = None

    def __init__(self):
        self.supported_filters = copy.deepcopy(self.__class__.supported_filters)
        self.supported_filters.update(RESERVED_QUERY_PARAMS)
        self.get_one_db_method = self._get_by_name_or_id

    @jsexpose()
    def get_all(self, **kwargs):
        return self._get_all(**kwargs)

    @jsexpose(arg_types=[str])
    def get_one(self, id):
        return self._get_one_by_id(id=id)

    def _get_all(self, exclude_fields=None, sort=None, offset=0, limit=None, query_options=None,
                 from_model_kwargs=None, **kwargs):
        """
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        """
        kwargs = copy.deepcopy(kwargs)

        exclude_fields = exclude_fields or []
        query_options = query_options if query_options else self.query_options

        # TODO: Why do we use comma delimited string, user can just specify
        # multiple values using ?sort=foo&sort=bar and we get a list back
        sort = sort.split(',') if sort else []

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

        default_sort_values = copy.copy(query_options.get('sort'))
        kwargs['sort'] = db_sort_values if db_sort_values else default_sort_values

        # TODO: To protect us from DoS, we need to make max_limit mandatory
        offset = int(offset)

        if limit and int(limit) > self.max_limit:
            # TODO: We should throw here, I don't like this.
            msg = 'Limit "%s" specified, maximum value is "%s"' % (limit, self.max_limit)
            raise ValueError(msg)

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

        extra = {
            'filters': filters,
            'sort': sort,
            'offset': offset,
            'limit': limit
        }
        LOG.info('GET all %s with filters=%s' % (pecan.request.path, filters), extra=extra)

        instances = self.access.query(exclude_fields=exclude_fields, **filters)
        if limit == 1:
            # Perform the filtering on the DB side
            instances = instances.limit(limit)

        if limit:
            pecan.response.headers['X-Limit'] = str(limit)
        pecan.response.headers['X-Total-Count'] = str(instances.count())

        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self._get_from_model_kwargs_for_request(request=pecan.request))

        result = []
        for instance in instances[offset:eop]:
            item = self.model.from_model(instance, **from_model_kwargs)
            result.append(item)

        return result

    def _get_one(self, id, exclude_fields=None):
        # Note: This is here for backward compatibility reasons
        return self._get_one_by_id(id=id, exclude_fields=exclude_fields)

    def _get_one_by_id(self, id, exclude_fields=None, from_model_kwargs=None):
        """
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        """

        LOG.info('GET %s with id=%s', pecan.request.path, id)

        instance = self._get_by_id(resource_id=id, exclude_fields=exclude_fields)

        if not instance:
            msg = 'Unable to identify resource with id "%s".' % id
            pecan.abort(http_client.NOT_FOUND, msg)

        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self._get_from_model_kwargs_for_request(request=pecan.request))
        result = self.model.from_model(instance, **from_model_kwargs)
        LOG.debug('GET %s with id=%s, client_result=%s', pecan.request.path, id, result)

        return result

    def _get_one_by_name_or_id(self, name_or_id, exclude_fields=None, from_model_kwargs=None):
        """
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        """

        LOG.info('GET %s with name_or_id=%s', pecan.request.path, name_or_id)

        instance = self._get_by_name_or_id(name_or_id=name_or_id, exclude_fields=exclude_fields)

        if not instance:
            msg = 'Unable to identify resource with name_or_id "%s".' % (name_or_id)
            pecan.abort(http_client.NOT_FOUND, msg)

        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self._get_from_model_kwargs_for_request(request=pecan.request))
        result = self.model.from_model(instance, **from_model_kwargs)
        LOG.debug('GET %s with name_or_id=%s, client_result=%s', pecan.request.path, id, result)

        return result

    def _get_one_by_pack_ref(self, pack_ref, exclude_fields=None, from_model_kwargs=None):
        LOG.info('GET %s with pack_ref=%s', pecan.request.path, pack_ref)

        instance = self._get_by_pack_ref(pack_ref=pack_ref, exclude_fields=exclude_fields)

        if not instance:
            msg = 'Unable to identify resource with pack_ref "%s".' % (pack_ref)
            pecan.abort(http_client.NOT_FOUND, msg)

        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self._get_from_model_kwargs_for_request(request=pecan.request))
        result = self.model.from_model(instance, **from_model_kwargs)
        LOG.debug('GET %s with pack_ref=%s, client_result=%s', pecan.request.path, id, result)

        return result

    def _get_by_id(self, resource_id, exclude_fields=None):
        try:
            resource_db = self.access.get(id=resource_id, exclude_fields=exclude_fields)
        except ValidationError:
            resource_db = None

        return resource_db

    def _get_by_name(self, resource_name, exclude_fields=None):
        try:
            resource_db = self.access.get(name=resource_name, exclude_fields=exclude_fields)
        except Exception:
            resource_db = None

        return resource_db

    def _get_by_pack_ref(self, pack_ref, exclude_fields=None):
        try:
            resource_db = self.access.get(pack=pack_ref, exclude_fields=exclude_fields)
        except Exception:
            resource_db = None

        return resource_db

    def _get_by_name_or_id(self, name_or_id, exclude_fields=None):
        """
        Retrieve resource object by an id of a name.
        """
        resource_db = self._get_by_id(resource_id=name_or_id, exclude_fields=exclude_fields)

        if not resource_db:
            # Try name
            resource_db = self._get_by_name(resource_name=name_or_id, exclude_fields=exclude_fields)

        if not resource_db:
            msg = 'Resource with a name or id "%s" not found' % (name_or_id)
            raise StackStormDBObjectNotFoundError(msg)

        return resource_db

    def _get_from_model_kwargs_for_request(self, request):
        """
        Retrieve kwargs which are passed to "LiveActionAPI.model" method.

        :param request: Pecan request object.

        :rtype: ``dict``
        """
        return self.from_model_kwargs

    def _get_one_by_scope_and_name(self, scope, name, from_model_kwargs=None):
        """
        Retrieve an item given scope and name. Only KeyValuePair now has concept of 'scope'.

        :param scope: Scope the key belongs to.
        :type scope: ``str``

        :param name: Name of the key.
        :type name: ``str``
        """
        instance = self.access.get_by_scope_and_name(scope=scope, name=name)
        if not instance:
            msg = 'KeyValuePair with name: %s and scope: %s not found in db.' % (name, scope)
            raise StackStormDBObjectNotFoundError(msg)
        from_model_kwargs = from_model_kwargs or {}
        result = self.model.from_model(instance, **from_model_kwargs)
        LOG.debug('GET with scope=%s and name=%s, client_result=%s', scope, name, result)

        return result

    def _validate_exclude_fields(self, exclude_fields):
        """
        Validate that provided exclude fields are valid.
        """
        if not exclude_fields:
            return exclude_fields

        for field in exclude_fields:
            if field not in self.valid_exclude_attributes:
                msg = 'Invalid or unsupported attribute specified: %s' % (field)
                raise ValueError(msg)

        return exclude_fields


class ContentPackResourceController(ResourceController):
    include_reference = False

    def __init__(self):
        super(ContentPackResourceController, self).__init__()
        self.get_one_db_method = self._get_by_ref_or_id

    @jsexpose(arg_types=[str])
    def get_one(self, ref_or_id, from_model_kwargs=None):
        return self._get_one(ref_or_id, from_model_kwargs=from_model_kwargs)

    @jsexpose()
    def get_all(self, **kwargs):
        return self._get_all(**kwargs)

    def _get_one(self, ref_or_id, exclude_fields=None, from_model_kwargs=None):
        LOG.info('GET %s with ref_or_id=%s', pecan.request.path, ref_or_id)

        try:
            instance = self._get_by_ref_or_id(ref_or_id=ref_or_id, exclude_fields=exclude_fields)
        except Exception as e:
            LOG.exception(e.message)
            pecan.abort(http_client.NOT_FOUND, e.message)
            return

        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self._get_from_model_kwargs_for_request(request=pecan.request))
        result = self.model.from_model(instance, **from_model_kwargs)
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

    def _get_by_ref_or_id(self, ref_or_id, exclude_fields=None):
        """
        Retrieve resource object by an id of a reference.

        Note: This method throws StackStormDBObjectNotFoundError exception if the object is not
        found in the database.
        """

        if ResourceReference.is_resource_reference(ref_or_id):
            # references always contain a dot and id's can't contain it
            is_reference = True
        else:
            is_reference = False

        if is_reference:
            resource_db = self._get_by_ref(resource_ref=ref_or_id, exclude_fields=exclude_fields)
        else:
            resource_db = self._get_by_id(resource_id=ref_or_id, exclude_fields=exclude_fields)

        if not resource_db:
            msg = 'Resource with a reference or id "%s" not found' % (ref_or_id)
            raise StackStormDBObjectNotFoundError(msg)

        return resource_db

    def _get_by_ref(self, resource_ref, exclude_fields=None):
        try:
            ref = ResourceReference.from_string_reference(ref=resource_ref)
        except Exception:
            return None

        resource_db = self.access.query(name=ref.name, pack=ref.pack,
                                        exclude_fields=exclude_fields).first()
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
