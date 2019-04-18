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

import logging

from st2client.models import core


LOG = logging.getLogger(__name__)


class KeyValuePair(core.Resource):
    _alias = 'Key'
    _display_name = 'Key Value Pair'
    _plural = 'Keys'
    _plural_display_name = 'Key Value Pairs'
    _repr_attributes = ['name', 'value']

    # Note: This is a temporary hack until we refactor client and make it support non id PKs
    def get_id(self):
        return self.name

    def set_id(self, value):
        pass

    id = property(get_id, set_id)
