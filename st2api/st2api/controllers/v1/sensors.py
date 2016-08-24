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
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_db_permission

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

    @request_user_has_permission(permission_type=PermissionType.SENSOR_LIST)
    @jsexpose()
    def get_all(self, **kwargs):
        return super(SensorTypeController, self)._get_all(**kwargs)

    @request_user_has_resource_db_permission(permission_type=PermissionType.SENSOR_VIEW)
    @jsexpose(arg_types=[str])
    def get_one(self, ref_or_id):
        return super(SensorTypeController, self)._get_one(ref_or_id)

    @request_user_has_resource_db_permission(permission_type=PermissionType.SENSOR_MODIFY)
    @jsexpose(arg_types=[str], body_cls=SensorTypeAPI)
    def put(self, sensor_type, ref_or_id):
        # Note: Right now this function only supports updating of "enabled"
        # attribute on the SensorType model.
        # The reason for that is that SensorTypeAPI.to_model right now only
        # knows how to work with sensor type definitions from YAML files.
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
            return

        if not getattr(sensor_type, 'pack', None):
            sensor_type.pack = sensor_type_db.pack
        try:
            old_sensor_type_db = sensor_type_db
            sensor_type_db.id = sensor_type_id
            sensor_type_db.enabled = getattr(sensor_type, 'enabled', False)
            sensor_type_db = SensorType.add_or_update(sensor_type_db)
        except (ValidationError, ValueError) as e:
            LOG.exception('Unable to update sensor_type data=%s', sensor_type)
            abort(http_client.BAD_REQUEST, str(e))
            return

        extra = {
            'old_sensor_type_db': old_sensor_type_db,
            'new_sensor_type_db': sensor_type_db
        }
        LOG.audit('Sensor updated. Sensor.id=%s.' % (sensor_type_db.id), extra=extra)
        sensor_type_api = SensorTypeAPI.from_model(sensor_type_db)

        return sensor_type_api
