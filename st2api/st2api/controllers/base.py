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

import six
from pecan.rest import RestController
from oslo_config import cfg
from six.moves.urllib import parse as urlparse  # pylint: disable=import-error

from st2api.controllers.controller_transforms import transform_to_bool
from st2common.rbac.utils import request_user_is_admin

__all__ = [
    'BaseRestControllerMixin',
    'SHOW_SECRETS_QUERY_PARAM'
]


SHOW_SECRETS_QUERY_PARAM = 'show_secrets'


class BaseRestControllerMixin(RestController):
    """
    Base REST controller class which contains various utility functions.
    """

    def _parse_query_params(self, request):
        """
        Parse query string for the provided request.

        :rtype: ``dict``
        """
        query_string = request.query_string
        query_params = dict(urlparse.parse_qsl(query_string))

        return query_params

    def _get_query_param_value(self, request, param_name, param_type, default_value=None):
        """
        Return a value for the provided query param and optionally cast it for boolean types.

        If the requested query parameter is not provided, default value is returned instead.

        :param request: Request object.

        :param param_name: Name of the param to retrieve the value for.
        :type param_name: ``str``

        :param param_type: Type of the query param (e.g. "bool").
        :type param_type: ``str``

        :param default_value: Value to return if query param is not provided.
        :type default_value: ``object``
        """
        query_params = self._parse_query_params(request=request)
        value = query_params.get(param_name, default_value)

        if param_type == 'bool' and isinstance(value, six.string_types):
            value = transform_to_bool(value)

        return value

    def _get_mask_secrets(self, request):
        """
        Return a value for mask_secrets which can be used in masking secret properties
        to be retruned by any API. The default value is as per the config however admin
        users have the ability to override by passing in a special query parameter
        ?show_secrets=True.

        :param request: Request object.

        :rtype: ``bool``
        """
        mask_secrets = cfg.CONF.api.mask_secrets
        show_secrets = self._get_query_param_value(request=request,
                                                   param_name=SHOW_SECRETS_QUERY_PARAM,
                                                   param_type='bool',
                                                   default_value=False)

        if show_secrets and request_user_is_admin(request=request):
            mask_secrets = False

        return mask_secrets
