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

import pecan

from st2common.constants.keyvalue import USER_SCOPE
from st2common.services import packs as packs_service
from st2common.models.api.base import jsexpose
from st2api.controllers.resource import ResourceController
from st2common.models.api.pack import ConfigAPI
from st2common.models.api.pack import ConfigItemSetAPI
from st2common.persistence.pack import Config
from st2common.persistence.pack import ConfigSchema
from st2common.services.config import set_datastore_value_for_config_key
from st2common.rbac.utils import get_user_db_from_request
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_db_permission

__all__ = [
    'PackConfigsController'
]


class PackConfigsController(ResourceController):
    model = ConfigAPI
    access = Config
    supported_filters = {}

    def __init__(self):
        super(PackConfigsController, self).__init__()

        # Note: This method is used to retrieve object for RBAC purposes and in
        # this case, RBAC is checked on the parent PackDB object
        self.get_one_db_method = packs_service.get_pack_by_ref

    @request_user_has_permission(permission_type=PermissionType.PACK_LIST)
    @jsexpose()
    def get_all(self, **kwargs):
        """
        Retrieve configs for all the packs.

        Handles requests:
            GET /configs/
        """
        # TODO: Make sure secret values are masked

        return super(PackConfigsController, self)._get_all(**kwargs)

    @request_user_has_resource_db_permission(permission_type=PermissionType.PACK_VIEW)
    @jsexpose(arg_types=[str])
    def get_one(self, pack_ref):
        """
        Retrieve config for a particular pack.

        Handles requests:
            GET /configs/<pack_ref>
        """
        # TODO: Make sure secret values are masked
        return self._get_one_by_pack_ref(pack_ref=pack_ref)

    @jsexpose(arg_types=[str], body_cls=ConfigItemSetAPI)
    def put(self, pack_ref, config_item_api):
        """
        Set a value for a dynamic pack config item.

        Handles requests:
            PUT /configs/<pack_ref>
        """
        name = config_item_api.name
        value = config_item_api.value
        scope = config_item_api.scope

        # TODO: Also validate value type against config schema
        config_schema_db = ConfigSchema.get_by_pack(value=pack_ref)

        config_item_schema = config_schema_db.attributes.get(name, {})
        if not config_item_schema:
            msg = ('Config schema for pack "%s" is missing schema definition for attribute "%s"' %
                   (pack_ref, name))
            raise ValueError(msg)

        # Note: Right now when "scope" is "user" we set user to the currently authenticated user.
        # TODO: We should probably support for admin to set "user" to arbitrary user in the system
        # TODO add log statements
        if scope == USER_SCOPE:
            user_db = get_user_db_from_request(request=pecan.request)
            if not user_db:
                msg = 'Unable to retrieve user from request. Is authentication enabled?'
                raise ValueError(msg)

            user = user_db.name
        else:
            user = None

        set_datastore_value_for_config_key(pack_name=pack_ref,
                                           key_name=name,
                                           user=user,
                                           value=value,
                                           secret=secret)

        config_api = self._get_one_by_pack_ref(pack_ref=pack_ref)
        return config_api
