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
from st2common import log as logging
from st2common.persistence.reactor import SensorType
from st2common.models.api.reactor import SensorTypeAPI
from st2api.controllers import resource

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class SensorTypeController(resource.ContentPackResourceController):
    model = SensorTypeAPI
    access = SensorType
    supported_filters = {
        'name': 'name',
        'pack': 'pack'
    }

    options = {
        'sort': ['pack', 'name']
    }

    include_reference = True
