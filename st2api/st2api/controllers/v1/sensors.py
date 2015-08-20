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
from pecan import abort
from mongoengine import ValidationError

from st2common import log as logging
from st2common.models.api.base import jsexpose
from st2common.persistence.sensor import SensorType
from st2common.models.api.sensor import SensorTypeAPI
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.validators.api.misc import validate_not_part_of_system_pack
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

    @jsexpose(str, body_cls=SensorTypeAPI)
    def put(self, ref_or_id, sensor_type):
        try:
            sensor_type_db = self._get_by_ref_or_id(ref_or_id=ref_or_id)
        except Exception as e:
            LOG.exception(e.message)
            abort(http_client.NOT_FOUND, e.message)
            return

        sensor_type_id = sensor_type_db.id

        try:
            validate_not_part_of_system_pack(sensor_type_db)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, str(e))

        if not getattr(sensor_type, 'pack', None):
            sensor_type.pack = sensor_type_db.pack

        try:
            sensor_type_db = SensorTypeAPI.to_model(sensor_type)
            sensor_type_db.id = sensor_type_id
            sensor_type_db = SensorType.add_or_update(sensor_type_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Unable to update sensor_type data=%s', sensor_type)
            abort(http_client.BAD_REQUEST, str(e))
            return

        sensor_type_api = SensorTypeAPI.from_model(sensor_type_db)
        LOG.debug('PUT /sensors/ client_result=%s', sensor_type_api)

        return sensor_type_api
