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

import logging

from st2client.models import core


LOG = logging.getLogger(__name__)


class Token(core.Resource):
    _display_name = 'Access Token'
    _plural = 'Tokens'
    _plural_display_name = 'Access Tokens'
    _repr_attributes = ['user', 'expiry', 'metadata']


class ApiKey(core.Resource):
    _display_name = 'API Key'
    _plural = 'ApiKeys'
    _plural_display_name = 'API Keys'
    _repr_attributes = ['id', 'user', 'metadata']
