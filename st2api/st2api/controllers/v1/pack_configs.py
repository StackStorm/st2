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

import os
import six

import jsonschema
from oslo_config import cfg
import yaml

from st2common import log as logging
from st2common.models.api.base import jsexpose
from st2api.controllers.resource import ResourceController
from st2common.bootstrap.configsregistrar import ConfigsRegistrar
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.services import packs as packs_service
from st2common.models.api.pack import ConfigAPI
from st2common.models.api.pack import ConfigUpdateRequestAPI
from st2common.persistence.pack import Config
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_db_permission

http_client = six.moves.http_client

__all__ = [
    'PackConfigsController'
]

LOG = logging.getLogger(__name__)


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

    @request_user_has_permission(permission_type=PermissionType.PACK_CONFIG)
    @jsexpose(body_cls=ConfigUpdateRequestAPI, arg_types=[str])
    def put(self, pack_uninstall_request, pack_ref):
        """
            Create a new config for a pack.

            Handles requests:
                POST /configs/<pack_ref>
        """

        try:
            config_api = ConfigAPI(pack=pack_ref, values=vars(pack_uninstall_request))
            config_api.validate(validate_against_schema=True)
        except jsonschema.ValidationError as e:
            raise ValueValidationException(str(e))

        config_content = yaml.safe_dump(config_api.values, default_flow_style=False)

        configs_path = os.path.join(cfg.CONF.system.base_path, 'configs/')
        config_path = os.path.join(configs_path, '%s.yaml' % config_api.pack)
        with open(config_path, 'w') as f:
            f.write(config_content)

        ConfigsRegistrar.save_model(config_api)

        return config_api
