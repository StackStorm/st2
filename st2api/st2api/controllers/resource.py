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
from mongoengine import ValidationError, LookUpError
import six
from six.moves import http_client

from st2common import log as logging
from st2common.models.system.common import ResourceReference
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.exceptions.rbac import ResourceAccessDeniedPermissionIsolationError
from st2common.rbac.backends import get_rbac_backend
from st2common.exceptions.rbac import AccessDeniedError
from st2common.util import schema as util_schema
from st2common.router import abort
from st2common.router import Response

LOG = logging.getLogger(__name__)

RESERVED_QUERY_PARAMS = {
    'id': 'id',
    'name': 'name',
    'sort': 'order_by'
}


def split_id_value(value):
    if not value or isinstance(value, (list, tuple)):
        return value

    split = value.split(',')

    if len(split) > 100:
        raise ValueError('Maximum of 100 items can be provided for a query parameter value')

    return split


DEFAULT_FILTER_TRANSFORM_FUNCTIONS = {
    # Support for filtering on multiple ids when a commona delimited string is provided
    # (e.g. ?id=1,2,3)
    'id': split_id_value
}


def parameter_validation(validator, properties, instance, schema):
    parameter_specific_schema = {
        "description": "Input parameters for the action.",
        "type": "object",
        "patternProperties": {
            r"^\w+$": util_schema.get_action_parameters_schema()
        },
        'additionalProperties': False,
        "default": {}
    }

    parameter_specific_validator = util_schema.CustomValidator(parameter_specific_schema)

    for error in parameter_specific_validator.iter_errors(instance=instance):
        yield error


@six.add_metaclass(abc.ABCMeta)
class ResourceController(object):
    model = abc.abstractproperty
    access = abc.abstractproperty
    supported_filters = abc.abstractproperty

    # Default kwargs passed to "APIClass.from_model" method
    from_model_kwargs = {}

    # Mandatory model attributes which are always retrieved from the database when using
    # ?include_attributes filter. Those attributes need to be included because a lot of code
    # depends on compound references and primary keys. In addition to that, it's needed for secrets
    # masking to work, etc.
    mandatory_include_fields_retrieve = ['id']

    # A list of fields which are always included in the response when ?include_attributes filter is
    # used. Those are things such as primary keys and similar.
    mandatory_include_fields_response = ['id']

    # Default number of items returned per page if no limit is explicitly provided
    default_limit = 100

    query_options = {
        'sort': []
    }

    # A list of optional transformation functions for user provided filter values
    filter_transform_functions = {}

    # A list of attributes which can be specified using ?exclude_attributes filter
    # If not provided, no validation is performed.
    valid_exclude_attributes = []

    # Method responsible for retrieving an instance of the corresponding model DB object
    # Note: This method should throw StackStormDBObjectNotFoundError if the corresponding DB
    # object doesn't exist
    get_one_db_method = None

    def __init__(self):
        self.supported_filters = copy.deepcopy(self.__class__.supported_filters)
        self.supported_filters.update(RESERVED_QUERY_PARAMS)

        self.filter_transform_functions = copy.deepcopy(self.__class__.filter_transform_functions)
        self.filter_transform_functions.update(DEFAULT_FILTER_TRANSFORM_FUNCTIONS)

        self.get_one_db_method = self._get_by_name_or_id

    # Maximum value of limit which can be specified by user
    @property
    def max_limit(self):
        return cfg.CONF.api.max_page_size

    def _get_all(self, exclude_fields=None, include_fields=None, advanced_filters=None,
                 sort=None, offset=0, limit=None, query_options=None,
                 from_model_kwargs=None, raw_filters=None, requester_user=None):
        """
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        """
        raw_filters = copy.deepcopy(raw_filters) or {}

        exclude_fields = exclude_fields or []
        include_fields = include_fields or []
        query_options = query_options if query_options else self.query_options

        if exclude_fields and include_fields:
            msg = ('exclude_fields and include_fields arguments are mutually exclusive. '
                   'You need to provide either one or another, but not both.')
            raise ValueError(msg)

        exclude_fields = self._validate_exclude_fields(exclude_fields=exclude_fields)
        include_fields = self._validate_include_fields(include_fields=include_fields)

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
        raw_filters['sort'] = db_sort_values if db_sort_values else default_sort_values

        # TODO: To protect us from DoS, we need to make max_limit mandatory
        offset = int(offset)
        if offset >= 2**31:
            raise ValueError('Offset "%s" specified is more than 32-bit int' % (offset))

        limit = validate_limit_query_param(limit=limit, requester_user=requester_user)
        eop = offset + int(limit) if limit else None

        filters = {}
        for k, v in six.iteritems(self.supported_filters):
            filter_value = raw_filters.get(k, None)

            if not filter_value:
                continue

            value_transform_function = self.filter_transform_functions.get(k, None)
            value_transform_function = value_transform_function or (lambda value: value)
            filter_value = value_transform_function(value=filter_value)

            if k in ['id', 'name'] and isinstance(filter_value, list):
                filters[k + '__in'] = filter_value
            else:
                field_name_split = v.split('.')

                # Make sure filter value is a list when using "in" filter
                if field_name_split[-1] == 'in' and not isinstance(filter_value, (list, tuple)):
                    filter_value = [filter_value]

                filters['__'.join(field_name_split)] = filter_value

        if advanced_filters:
            for token in advanced_filters.split(' '):
                try:
                    [k, v] = token.split(':', 1)
                except ValueError:
                    raise ValueError('invalid format for filter "%s"' % token)
                path = k.split('.')
                try:
                    self.model.model._lookup_field(path)
                    filters['__'.join(path)] = v
                except LookUpError as e:
                    raise ValueError(six.text_type(e))

        instances = self.access.query(exclude_fields=exclude_fields, only_fields=include_fields,
                                      **filters)
        if limit == 1:
            # Perform the filtering on the DB side
            instances = instances.limit(limit)

        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self.from_model_kwargs)

        result = self.resources_model_filter(model=self.model,
                                             instances=instances,
                                             offset=offset,
                                             eop=eop,
                                             requester_user=requester_user,
                                             **from_model_kwargs)

        resp = Response(json=result)
        resp.headers['X-Total-Count'] = str(instances.count())

        if limit:
            resp.headers['X-Limit'] = str(limit)

        return resp

    def resources_model_filter(self, model, instances, requester_user=None, offset=0, eop=0,
                              **from_model_kwargs):
        """
        Method which converts DB objects to API objects and performs any additional filtering.
        """

        result = []
        for instance in instances[offset:eop]:
            item = self.resource_model_filter(model=model, instance=instance,
                                              requester_user=requester_user,
                                              **from_model_kwargs)
            result.append(item)
        return result

    def resource_model_filter(self, model, instance, requester_user=None, **from_model_kwargs):
        """
        Method which converts DB object to API object and performs any additional filtering.
        """
        item = model.from_model(instance, **from_model_kwargs)
        return item

    def _get_one_by_id(self, id, requester_user, permission_type, exclude_fields=None,
                       include_fields=None, from_model_kwargs=None):
        """
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        :param include_fields: A list of object fields to include.
        :type include_fields: ``list``
        """

        instance = self._get_by_id(resource_id=id, exclude_fields=exclude_fields,
                                   include_fields=include_fields)

        if permission_type:
            rbac_utils = get_rbac_backend().get_utils_class()
            rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                              resource_db=instance,
                                                              permission_type=permission_type)

        if not instance:
            msg = 'Unable to identify resource with id "%s".' % id
            abort(http_client.NOT_FOUND, msg)

        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self.from_model_kwargs)

        result = self.resource_model_filter(model=self.model, instance=instance,
                                            requester_user=requester_user,
                                            **from_model_kwargs)

        if not result:
            LOG.debug('Not returning the result because RBAC resource isolation is enabled and '
                      'current user doesn\'t match the resource user')
            raise ResourceAccessDeniedPermissionIsolationError(user_db=requester_user,
                                                               resource_api_or_db=instance,
                                                               permission_type=permission_type)

        return result

    def _get_one_by_name_or_id(self, name_or_id, requester_user, permission_type,
                               exclude_fields=None, include_fields=None, from_model_kwargs=None):
        """
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        :param include_fields: A list of object fields to include.
        :type include_fields: ``list``
        """

        instance = self._get_by_name_or_id(name_or_id=name_or_id, exclude_fields=exclude_fields,
                                           include_fields=include_fields)

        if permission_type:
            rbac_utils = get_rbac_backend().get_utils_class()
            rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                              resource_db=instance,
                                                              permission_type=permission_type)

        if not instance:
            msg = 'Unable to identify resource with name_or_id "%s".' % (name_or_id)
            abort(http_client.NOT_FOUND, msg)

        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self.from_model_kwargs)
        result = self.model.from_model(instance, **from_model_kwargs)

        return result

    def _get_one_by_pack_ref(self, pack_ref, exclude_fields=None, include_fields=None,
                             from_model_kwargs=None):
        instance = self._get_by_pack_ref(pack_ref=pack_ref, exclude_fields=exclude_fields,
                                         include_fields=include_fields)

        if not instance:
            msg = 'Unable to identify resource with pack_ref "%s".' % (pack_ref)
            abort(http_client.NOT_FOUND, msg)

        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self.from_model_kwargs)
        result = self.model.from_model(instance, **from_model_kwargs)

        return result

    def _get_by_id(self, resource_id, exclude_fields=None, include_fields=None):
        try:
            resource_db = self.access.get(id=resource_id, exclude_fields=exclude_fields,
                                          only_fields=include_fields)
        except ValidationError:
            resource_db = None

        return resource_db

    def _get_by_name(self, resource_name, exclude_fields=None, include_fields=None):
        try:
            resource_db = self.access.get(name=resource_name, exclude_fields=exclude_fields,
                                          only_fields=include_fields)
        except Exception:
            resource_db = None

        return resource_db

    def _get_by_pack_ref(self, pack_ref, exclude_fields=None, include_fields=None):
        try:
            resource_db = self.access.get(pack=pack_ref, exclude_fields=exclude_fields,
                                          only_fields=include_fields)
        except Exception:
            resource_db = None

        return resource_db

    def _get_by_name_or_id(self, name_or_id, exclude_fields=None, include_fields=None):
        """
        Retrieve resource object by an id of a name.
        """
        resource_db = self._get_by_id(resource_id=name_or_id, exclude_fields=exclude_fields,
                                      include_fields=include_fields)

        if not resource_db:
            # Try name
            resource_db = self._get_by_name(resource_name=name_or_id,
                                            exclude_fields=exclude_fields)

        if not resource_db:
            msg = 'Resource with a name or id "%s" not found' % (name_or_id)
            raise StackStormDBObjectNotFoundError(msg)

        return resource_db

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

        if not self.valid_exclude_attributes:
            return exclude_fields

        for field in exclude_fields:
            if field not in self.valid_exclude_attributes:
                msg = ('Invalid or unsupported exclude attribute specified: %s' % (field))
                raise ValueError(msg)

        return exclude_fields

    def _validate_include_fields(self, include_fields):
        """
        Validate that provided include fields are valid.
        """
        if not include_fields:
            return include_fields

        result = copy.copy(include_fields)
        for field in self.mandatory_include_fields_retrieve:
            # Don't add mandatory field if user already requested the whole dict object (e.g. user
            # requests action and action.parameters is a mandatory field)
            partial_field = field.split('.')[0]
            if partial_field in include_fields:
                continue

            result.append(field)
        result = list(set(result))

        return result


class BaseResourceIsolationControllerMixin(object):
    """
    Base API controller which isolates resources for users. Users can only see their own resources.

    Exceptions include admin and system user which can view all the resources (also for other
    users).
    """

    def resources_model_filter(self, model, instances, requester_user=None, offset=0, eop=0,
                              **from_model_kwargs):
        # RBAC or permission isolation is disabled, bail out
        if not (cfg.CONF.rbac.enable and cfg.CONF.rbac.permission_isolation):
            result = super(BaseResourceIsolationControllerMixin, self).resources_model_filter(
                model=model, instances=instances, requester_user=requester_user,
                offset=offset, eop=eop, **from_model_kwargs)

            return result

        result = []
        for instance in instances[offset:eop]:
            item = self.resource_model_filter(model=model, instance=instance,
                                              requester_user=requester_user, **from_model_kwargs)

            if not item:
                continue

            result.append(item)

        return result

    def resource_model_filter(self, model, instance, requester_user=None, **from_model_kwargs):
        # RBAC or permission isolation is disabled, bail out
        if not (cfg.CONF.rbac.enable and cfg.CONF.rbac.permission_isolation):
            result = super(BaseResourceIsolationControllerMixin, self).resource_model_filter(
                model=model, instance=instance, requester_user=requester_user,
                **from_model_kwargs)

            return result

        rbac_utils = get_rbac_backend().get_utils_class()
        user_is_admin = rbac_utils.user_is_admin(user_db=requester_user)
        user_is_system_user = (requester_user.name == cfg.CONF.system_user.user)

        item = model.from_model(instance, **from_model_kwargs)

        # Admin users and system users can view all the resoruces
        if user_is_admin or user_is_system_user:
            return item

        user = item.context.get('user', None)
        if user and (user == requester_user.name):
            return item

        return None


class ContentPackResourceController(ResourceController):
    # name and pack are mandatory because they compromise primary key - reference (<pack>.<name>)
    mandatory_include_fields_retrieve = ['pack', 'name']

    # A list of fields which are always included in the response. Those are things such as primary
    # keys and similar
    mandatory_include_fields_response = ['id', 'ref']

    def __init__(self):
        super(ContentPackResourceController, self).__init__()
        self.get_one_db_method = self._get_by_ref_or_id

    def _get_one(self, ref_or_id, requester_user, permission_type, exclude_fields=None,
                 include_fields=None, from_model_kwargs=None):
        try:
            instance = self._get_by_ref_or_id(ref_or_id=ref_or_id, exclude_fields=exclude_fields,
                                              include_fields=include_fields)
        except Exception as e:
            LOG.exception(six.text_type(e))
            abort(http_client.NOT_FOUND, six.text_type(e))
            return

        if permission_type:
            rbac_utils = get_rbac_backend().get_utils_class()
            rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                              resource_db=instance,
                                                              permission_type=permission_type)

        # Perform resource isolation check (if supported)
        from_model_kwargs = from_model_kwargs or {}
        from_model_kwargs.update(self.from_model_kwargs)

        result = self.resource_model_filter(model=self.model, instance=instance,
                                            requester_user=requester_user,
                                            **from_model_kwargs)

        if not result:
            LOG.debug('Not returning the result because RBAC resource isolation is enabled and '
                      'current user doesn\'t match the resource user')
            raise ResourceAccessDeniedPermissionIsolationError(user_db=requester_user,
                                                               resource_api_or_db=instance,
                                                               permission_type=permission_type)

        return Response(json=result)

    def _get_all(self, exclude_fields=None, include_fields=None,
                 sort=None, offset=0, limit=None, query_options=None,
                 from_model_kwargs=None, raw_filters=None, requester_user=None):
        resp = super(ContentPackResourceController,
                     self)._get_all(exclude_fields=exclude_fields,
                                    include_fields=include_fields,
                                    sort=sort,
                                    offset=offset,
                                    limit=limit,
                                    query_options=query_options,
                                    from_model_kwargs=from_model_kwargs,
                                    raw_filters=raw_filters,
                                    requester_user=requester_user)

        return resp

    def _get_by_ref_or_id(self, ref_or_id, exclude_fields=None, include_fields=None):
        """
        Retrieve resource object by an id of a reference.

        Note: This method throws StackStormDBObjectNotFoundError exception if the object is not
        found in the database.
        """

        if exclude_fields and include_fields:
            msg = ('exclude_fields and include_fields arguments are mutually exclusive. '
                   'You need to provide either one or another, but not both.')
            raise ValueError(msg)

        if ResourceReference.is_resource_reference(ref_or_id):
            # references always contain a dot and id's can't contain it
            is_reference = True
        else:
            is_reference = False

        if is_reference:
            resource_db = self._get_by_ref(resource_ref=ref_or_id, exclude_fields=exclude_fields,
                                          include_fields=include_fields)
        else:
            resource_db = self._get_by_id(resource_id=ref_or_id, exclude_fields=exclude_fields,
                                          include_fields=include_fields)

        if not resource_db:
            msg = 'Resource with a reference or id "%s" not found' % (ref_or_id)
            raise StackStormDBObjectNotFoundError(msg)

        return resource_db

    def _get_by_ref(self, resource_ref, exclude_fields=None, include_fields=None):
        if exclude_fields and include_fields:
            msg = ('exclude_fields and include_fields arguments are mutually exclusive. '
                   'You need to provide either one or another, but not both.')
            raise ValueError(msg)

        try:
            ref = ResourceReference.from_string_reference(ref=resource_ref)
        except Exception:
            return None

        resource_db = self.access.query(name=ref.name, pack=ref.pack,
                                        exclude_fields=exclude_fields,
                                        only_fields=include_fields).first()
        return resource_db


def validate_limit_query_param(limit, requester_user=None):
    """
    Validate that the provided value for "limit" query parameter is valid.

    Note: We only perform max_page_size check for non-admin users. Admin users
    can provide arbitrary limit value.
    """
    rbac_utils = get_rbac_backend().get_utils_class()
    user_is_admin = rbac_utils.user_is_admin(user_db=requester_user)

    if limit:
        # Display all the results
        if int(limit) == -1:
            if not user_is_admin:
                # Only admins can specify limit -1
                message = ('Administrator access required to be able to specify limit=-1 and '
                           'retrieve all the records')
                raise AccessDeniedError(message=message,
                                        user_db=requester_user)

            return 0
        elif int(limit) <= -2:
            msg = 'Limit, "%s" specified, must be a positive number.' % (limit)
            raise ValueError(msg)
        elif int(limit) > cfg.CONF.api.max_page_size and not user_is_admin:
            msg = ('Limit "%s" specified, maximum value is "%s"' % (limit,
                                                                    cfg.CONF.api.max_page_size))

            raise AccessDeniedError(message=msg,
                                    user_db=requester_user)
    # Disable n = 0
    elif limit == 0:
        msg = ('Limit, "%s" specified, must be a positive number or -1 for full result set.' %
               (limit))
        raise ValueError(msg)

    return limit
