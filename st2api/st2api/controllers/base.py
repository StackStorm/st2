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

from pecan.rest import RestController
from six.moves.urllib import parse as urlparse

__all__ = [
    'BaseRestControllerMixin'
]


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
