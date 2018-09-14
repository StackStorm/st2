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

from webob import Request

from st2common import log as logging
from st2common.metrics.base import CounterWithTimer
from st2common.metrics.base import get_driver
from st2common.util.date import get_datetime_utc_now
from st2common.router import NotFoundException

__all__ = [
    'RequestInstrumentationMiddleware',
    'ResponseInstrumentationMiddleware'
]

LOG = logging.getLogger(__name__)


class RequestInstrumentationMiddleware(object):
    """
    Instrumentation middleware which records various request related metrics.
    """

    def __init__(self, app, router, service_name):
        """
        :param service_name: Service name (e.g. api, stream, auth).
        :type service_name: ``str``
        """
        self.app = app
        self.router = router
        self._service_name = service_name

    def __call__(self, environ, start_response):
        request = Request(environ)

        try:
            endpoint, _ = self.router.match(request)
        except NotFoundException:
            endpoint = {}

        # NOTE: We don't track per request and response metrics for /v1/executions/<id> and some
        # other endpoints because this would result in a lot of unique metrics which is an
        # anti-pattern and causes unnecessary load on the metrics server.
        submit_metrics = endpoint.get('x-submit-metrics', True)
        if not submit_metrics:
            LOG.debug('Not submitting request metrics for path: %s' % (request.path))
            return self.app(environ, start_response)

        metrics_driver = get_driver()

        key = '%s.request.total' % (self._service_name)
        metrics_driver.inc_counter(key)

        key = '%s.request.method.%s' % (self._service_name, request.method)
        metrics_driver.inc_counter(key)

        path = request.path.replace('/', '_')
        key = '%s.request.path.%s' % (self._service_name, path)
        metrics_driver.inc_counter(key)

        if self._service_name == 'stream':
            # For stream service, we also record current number of open connections.
            # Due to the way stream service works, we need to utilize eventlet posthook to
            # correctly set the counter when the connection is closed / full response is returned.
            # See http://eventlet.net/doc/modules/wsgi.html#non-standard-extension-to-support-post-
            # hooks for details

            # Increase request counter
            key = '%s.request' % (self._service_name)
            metrics_driver.inc_counter(key)

            # Increase "total number of connections" gauge
            metrics_driver.inc_gauge('stream.connections', 1)

            start_time = get_datetime_utc_now()

            def update_metrics_hook(env):
                # Hook which is called at the very end after all the response has been sent and
                # connection closed
                time_delta = (get_datetime_utc_now() - start_time)
                duration = time_delta.total_seconds()

                # Send total request time
                metrics_driver.time(key, duration)

                # Decrease "current number of connections" gauge
                metrics_driver.dec_gauge('stream.connections', 1)

            # NOTE: Some tests mock environ and there 'eventlet.posthooks' key is not available
            if 'eventlet.posthooks' in environ:
                environ['eventlet.posthooks'].append((update_metrics_hook, (), {}))

            return self.app(environ, start_response)
        else:
            # Track and time current number of processing requests
            key = '%s.request' % (self._service_name)

            with CounterWithTimer(key=key):
                return self.app(environ, start_response)


class ResponseInstrumentationMiddleware(object):
    """
    Instrumentation middleware which records various response related metrics.
    """

    def __init__(self, app, router, service_name):
        """
        :param service_name: Service name (e.g. api, stream, auth).
        :type service_name: ``str``
        """
        self.app = app
        self.router = router
        self._service_name = service_name

    def __call__(self, environ, start_response):
        # Track and time current number of processing requests
        def custom_start_response(status, headers, exc_info=None):
            status_code = int(status.split(' ')[0])

            metrics_driver = get_driver()
            metrics_driver.inc_counter('%s.response.status.%s' % (self._service_name,
                                                                  status_code))

            return start_response(status, headers, exc_info)

        return self.app(environ, custom_start_response)
