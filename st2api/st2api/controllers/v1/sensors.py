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

import six
from mongoengine import ValidationError

from st2common import log as logging
from st2common.persistence.sensor import SensorType
from st2common.persistence.sensor_instance import SensorInstance
from st2common.models.api.sensor import SensorTypeAPI
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.validators.api.misc import validate_not_part_of_system_pack
from st2common.util import isotime
from st2api.controllers import resource
from st2api.controllers.controller_transforms import transform_to_bool
from st2common.rbac.types import PermissionType
from st2common.rbac.backends import get_rbac_backend
from st2common.router import abort
from st2common.router import Response

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class SensorTypeController(resource.ContentPackResourceController):
    model = SensorTypeAPI
    access = SensorType
    supported_filters = {
        "name": "name",
        "pack": "pack",
        "enabled": "enabled",
        "trigger": "trigger_types",
        # "ref" maps to a "ref__in" filter so it accepts one or more refs. It is
        # also used internally to constrain results when filtering by "status"
        # (which lives in the separate SensorInstanceDB collection).
        "ref": "ref.in",
    }

    filter_transform_functions = {"enabled": transform_to_bool}

    options = {"sort": ["pack", "name"]}

    # Runtime health fields merged in from SensorInstanceDB (keyed by sensor ref).
    HEALTH_ATTRIBUTES = [
        "status",
        "hostname",
        "pid",
        "exit_code",
        "respawn_count",
    ]

    def get_all(
        self,
        exclude_attributes=None,
        include_attributes=None,
        sort=None,
        offset=0,
        limit=None,
        requester_user=None,
        **raw_filters,
    ):
        # "status" is not a SensorTypeDB field - it lives in SensorInstanceDB.
        # Resolve it to the set of matching sensor refs and constrain the query.
        status = raw_filters.pop("status", None)
        if status:
            try:
                refs = [
                    instance.ref
                    for instance in SensorInstance.query(
                        status=status, only_fields=["ref"]
                    )
                ]
            except Exception:
                LOG.warning(
                    "Failed to resolve sensor refs for status filter", exc_info=True
                )
                refs = []

            if not refs:
                resp = Response(json=[])
                resp.headers["X-Total-Count"] = "0"
                return resp

            raw_filters["ref"] = refs

        return super(SensorTypeController, self)._get_all(
            exclude_fields=exclude_attributes,
            include_fields=include_attributes,
            sort=sort,
            offset=offset,
            limit=limit,
            raw_filters=raw_filters,
            requester_user=requester_user,
        )

    def get_one(self, ref_or_id, requester_user):
        permission_type = PermissionType.SENSOR_VIEW
        return super(SensorTypeController, self)._get_one(
            ref_or_id, requester_user=requester_user, permission_type=permission_type
        )

    def resources_model_filter(
        self,
        model,
        instances,
        requester_user=None,
        offset=0,
        eop=0,
        **from_model_kwargs,
    ):
        # List path (get_all): batch-fetch health records once to avoid N+1.
        page = list(instances[offset:eop])
        health_by_ref = self._get_health_by_ref(
            [getattr(instance, "ref", None) for instance in page]
        )

        result = []
        for instance in page:
            # Call the base per-item converter directly (not self.resource_model_filter)
            # so we don't issue a second, per-item health query.
            item = super(SensorTypeController, self).resource_model_filter(
                model=model,
                instance=instance,
                requester_user=requester_user,
                **from_model_kwargs,
            )
            if item:
                self._apply_health(item, health_by_ref.get(instance.ref))
            result.append(item)
        return result

    def resource_model_filter(
        self, model, instance, requester_user=None, **from_model_kwargs
    ):
        # Single path (get_one): convert then merge runtime health.
        item = super(SensorTypeController, self).resource_model_filter(
            model=model,
            instance=instance,
            requester_user=requester_user,
            **from_model_kwargs,
        )
        if item:
            health_by_ref = self._get_health_by_ref([getattr(instance, "ref", None)])
            self._apply_health(item, health_by_ref.get(instance.ref))
        return item

    def _get_health_by_ref(self, refs):
        """
        Return a ``ref -> SensorInstanceDB`` map for the provided sensor refs.
        """
        refs = [ref for ref in refs if ref]
        if not refs:
            return {}

        try:
            instances = SensorInstance.query(ref__in=refs)
            return {instance.ref: instance for instance in instances}
        except Exception:
            LOG.warning("Failed to load sensor health records", exc_info=True)
            return {}

    def _apply_health(self, item, instance_db):
        """
        Merge runtime health fields from a SensorInstanceDB record onto the
        SensorTypeAPI instance. Fields default to None when no record exists.
        """
        for attribute in self.HEALTH_ATTRIBUTES:
            setattr(item, attribute, getattr(instance_db, attribute, None))

        updated_at = getattr(instance_db, "updated_at", None)
        item.updated_at = (
            isotime.format(updated_at, offset=False) if updated_at else None
        )

    def put(self, sensor_type, ref_or_id, requester_user):
        # Note: Right now this function only supports updating of "enabled"
        # attribute on the SensorType model.
        # The reason for that is that SensorTypeAPI.to_model right now only
        # knows how to work with sensor type definitions from YAML files.

        sensor_type_db = self._get_by_ref_or_id(ref_or_id=ref_or_id)

        permission_type = PermissionType.SENSOR_MODIFY
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(
            user_db=requester_user,
            resource_db=sensor_type_db,
            permission_type=permission_type,
        )

        sensor_type_id = sensor_type_db.id

        try:
            validate_not_part_of_system_pack(sensor_type_db)
        except ValueValidationException as e:
            abort(http_client.BAD_REQUEST, six.text_type(e))
            return

        if not getattr(sensor_type, "pack", None):
            sensor_type.pack = sensor_type_db.pack
        try:
            old_sensor_type_db = sensor_type_db
            sensor_type_db.id = sensor_type_id
            sensor_type_db.enabled = getattr(sensor_type, "enabled", False)
            sensor_type_db = SensorType.add_or_update(sensor_type_db)
        except (ValidationError, ValueError) as e:
            LOG.exception("Unable to update sensor_type data=%s", sensor_type)
            abort(http_client.BAD_REQUEST, six.text_type(e))
            return

        extra = {
            "old_sensor_type_db": old_sensor_type_db,
            "new_sensor_type_db": sensor_type_db,
        }
        LOG.audit("Sensor updated. Sensor.id=%s." % (sensor_type_db.id), extra=extra)
        sensor_type_api = SensorTypeAPI.from_model(sensor_type_db)

        return sensor_type_api


sensor_type_controller = SensorTypeController()
