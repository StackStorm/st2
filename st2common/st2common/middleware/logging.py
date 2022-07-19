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

import time
import types
import itertools

from oslo_config import cfg

from st2common.constants.api import REQUEST_ID_HEADER
from st2common.constants.auth import QUERY_PARAM_ATTRIBUTE_NAME
from st2common.constants.auth import QUERY_PARAM_API_KEY_ATTRIBUTE_NAME
from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE
from st2common.constants.secrets import MASKED_ATTRIBUTES_BLACKLIST
from st2common import log as logging
from st2common.router import Request, NotFoundException

LOG = logging.getLogger(__name__)

SECRET_QUERY_PARAMS = [
    QUERY_PARAM_ATTRIBUTE_NAME,
    QUERY_PARAM_API_KEY_ATTRIBUTE_NAME,
] + MASKED_ATTRIBUTES_BLACKLIST

try:
    clock = time.perf_counter
except AttributeError:
    clock = time.time


class LoggingMiddleware(object):
    """
    Logs all incoming requests and outgoing responses
    """

    def __init__(self, app, router):
        self.app = app
        self.router = router

    def __call__(self, environ, start_response):
        start_time = clock()
        status_code = []
        content_length = []

        request = Request(environ)

        query_params = request.GET.dict_of_lists()

        # Mask secret / sensitive query params
        secret_query_params = SECRET_QUERY_PARAMS + cfg.CONF.log.mask_secrets_blacklist
        for param_name in secret_query_params:
            if param_name in query_params:
                query_params[param_name] = MASKED_ATTRIBUTE_VALUE

        # Log the incoming request
        values = {
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
            "query": query_params,
            "request_id": request.headers.get(REQUEST_ID_HEADER, None),
        }

        LOG.info(
            "%(request_id)s - %(method)s %(path)s with query=%(query)s" % values,
            extra=values,
        )

        def custom_start_response(status, headers, exc_info=None):
            status_code.append(int(status.split(" ")[0]))

            for name, value in headers:
                if name.lower() == "content-length":
                    content_length.append(int(value))
                    break

            return start_response(status, headers, exc_info)

        retval = self.app(environ, custom_start_response)

        try:
            endpoint, path_vars = self.router.match(request)
        except NotFoundException:
            endpoint = {}

        log_result = endpoint.get("x-log-result", True)

        if isinstance(retval, (types.GeneratorType, itertools.chain)):
            # Note: We don't log the result when return value is a generator, because this would
            # result in calling str() on the generator and as such, exhausting it
            content_length = [0]
            log_result = False

        # Log the response
        values = {
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
            "status": status_code[0],
            "runtime": float("{0:.3f}".format((clock() - start_time) * 10**3)),
            "content_length": content_length[0]
            if content_length
            else len(b"".join(retval)),
            "request_id": request.headers.get(REQUEST_ID_HEADER, None),
        }

        log_msg = "%(request_id)s - %(status)s %(content_length)s %(runtime)sms" % (
            values
        )
        LOG.info(log_msg, extra=values)

        if log_result:
            values["result"] = retval[0]
            log_msg = (
                "%(request_id)s - %(status)s %(content_length)s %(runtime)sms\n%(result)s"
                % (values)
            )
            LOG.debug(log_msg, extra=values)

        return retval
