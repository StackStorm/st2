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

from __future__ import absolute_import
from st2common import __version__

__all__ = [
    'VERSION_STRING',

    'API_URL_ENV_VARIABLE_NAME',
    'AUTH_TOKEN_ENV_VARIABLE_NAME',
]

VERSION_STRING = 'StackStorm v%s' % (__version__)

API_URL_ENV_VARIABLE_NAME = 'ST2_API_URL'
AUTH_TOKEN_ENV_VARIABLE_NAME = 'ST2_AUTH_TOKEN'
