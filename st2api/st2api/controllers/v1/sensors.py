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
from mongoengine import ValidationError

from st2common import log as logging
from st2common.persistence.sensor import SensorType
from st2common.models.api.sensor import SensorTypeAPI
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.validators.api.misc import validate_not_part_of_system_pack
from st2api.controllers import resource
from st2api.controllers.controller_transforms import transform_to_bool
from st2common.rbac.types import PermissionType
from st2common.rbac.backends import get_rbac_backend
from st2common.router import abort

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class SensorTypeController(resource.ContentPackResourceController):
    model = SensorTypeAPI
    access = SensorType
    supported_filters = {
        'name': 'name',
        'pack': 'pack',
        'enabled': 'enabled',
        'trigger': 'trigger_types'
    }

    filter_transform_functions = {
        'enabled': transform_to_bool
    }

    options = {
        'sort': ['pack', 'name']
    }

    def get_all(self, exclude_attributes=None, include_attributes=None, sort=None, offset=0,
                limit=None, requester_user=None, **raw_filters):
        return super(SensorTypeController, self)._get_all(exclude_fields=exclude_attributes,
                                                          include_fields=include_attributes,
                                                          sort=sort,
                                                          offset=offset,
                                                          limit=limit,
                                                          raw_filters=raw_filters,
                                                          requester_user=requester_user)

    def get_one(self, ref_or_id, requester_user):
        permission_type = PermissionType.SENSOR_VIEW
        return super(SensorTypeController, self)._get_one(ref_or_id,
                                                          requester_user=requester_user,
                                                          permission_type=permission_type)

    def put(self, sensor_type, ref_or_id, requester_user):
        # Note: Right now this function only supports updating of "enabled"
        # attribute on the SensorType model.
        # The reason for that is that SensorTypeAPI.to_model right now only
        # knows how to work with sensor type definitions from YAML files.

        sensor_type_db = self._get_by_ref_or_id(ref_or_id=ref_or_id)

        permission_type = PermissionType.SENSOR_MODIFY
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=sensor_type_db,
                                                          permission_type=permission_type)

        sensor_type_id = sensor_type_db.id

        try:
            validate_not_part_of_system_pack(sensor_type_db)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, six.text_type(e))
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
            abort(http_client.BAD_REQUEST, six.text_type(e))
            return

        extra = {
            'old_sensor_type_db': old_sensor_type_db,
            'new_sensor_type_db': sensor_type_db
        }
        LOG.audit('Sensor updated. Sensor.id=%s.' % (sensor_type_db.id), extra=extra)
        sensor_type_api = SensorTypeAPI.from_model(sensor_type_db)

        return sensor_type_api


sensor_type_controller = SensorTypeController()
