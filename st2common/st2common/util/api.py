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

import re

import pecan
from oslo_config import cfg
from webob import exc as webob_exc

from st2common import log as logging
from st2common.constants.api import DEFAULT_API_VERSION
from st2common.util.url import get_url_without_trailing_slash

__all__ = [
    'get_base_public_api_url',
    'get_full_public_api_url',
    'get_mistral_api_url',

    'get_requester',
    'get_exception_for_type_error'

]

LOG = logging.getLogger(__name__)


def get_base_public_api_url():
    """
    Return full public URL to the API endpoint (excluding the API version).

    :rtype: ``str``
    """
    # Note: This is here for backward compatibility reasons - if api_url is not set we fall back
    # to the old approach (using api listen host and port)
    if cfg.CONF.auth.api_url:
        api_url = get_url_without_trailing_slash(cfg.CONF.auth.api_url)
    else:
        LOG.warn('"auth.api_url" configuration option is not configured')
        api_url = 'http://%s:%s' % (cfg.CONF.api.host, cfg.CONF.api.port)

    return api_url


def get_full_public_api_url(api_version=DEFAULT_API_VERSION):
    """
    Return full public URL to the API endpoint (including the API version).

    :rtype: ``str``
    """
    api_url = get_base_public_api_url()
    api_url = '%s/%s' % (api_url, api_version)
    return api_url


def get_mistral_api_url(api_version=DEFAULT_API_VERSION):
    """
    Return a URL which Mistral uses to talk back to the StackStorm API.

    Note: If not provided it defaults to the public API url.
    """
    if cfg.CONF.mistral.api_url:
        api_url = get_url_without_trailing_slash(cfg.CONF.mistral.api_url)
        api_url = '%s/%s' % (api_url, api_version)
    else:
        LOG.warn('"mistral.api_url" not set, using auth.api_url')
        api_url = get_full_public_api_url(api_version=api_version)

    return api_url


def get_requester():
    """
    Retrieve username of the authed user (note - if auth is disabled, user will not be
    set so we fall back to the system user name)

    :rtype: ``str``
    """
    auth_context = pecan.request.context.get('auth', None)
    user_db = auth_context.get('user', None) if auth_context else None

    if not user_db:
        LOG.warn('auth is disabled, falling back to system_user')
        username = cfg.CONF.system_user.user
    else:
        username = user_db.name

    return username


def get_exception_for_type_error(func, exc):
    """
    Method which translates TypeError thrown by the controller method and intercepted inside
    jsexpose decorator and returns a better exception for it.

    :param func: Controller function / method.
    :type func: ``callable``

    :param exc: Exception intercepted by jsexpose.
    :type exc: :class:`Exception`
    """
    message = str(exc)
    func_name = func.__name__

    # Note: Those checks are hacky, but it's better than having no checks and silently
    # accepting invalid requests
    invalid_num_args_pattern = ('%s\(\) takes %s \d+ arguments? \(\d+ given\)' %
                                (func_name, '(exactly|at most|at least)'))
    unexpected_keyword_arg_pattern = ('%s\(\) got an unexpected keyword argument \'(.*?)\'' %
                                      (func_name))

    if (re.search(invalid_num_args_pattern, message)):
        # Invalid number of arguments passed to the function meaning invalid path was
        # requested
        result = webob_exc.HTTPNotFound()
    elif re.search(unexpected_keyword_arg_pattern, message):
        # User passed in an unsupported query parameter
        match = re.match(unexpected_keyword_arg_pattern, message)

        if match:
            groups = match.groups()
            query_param_name = groups[0]

            msg = 'Unsupported query parameter: %s' % (query_param_name)
        else:
            msg = 'Unknown error, please contact the administrator.'
        result = webob_exc.HTTPBadRequest(detail=msg)
    else:
        result = exc

    return result
