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
from st2api.controllers.base import BaseRestControllerMixin
from st2api.controllers.resource import ResourceController
from st2common.bootstrap.configsregistrar import ConfigsRegistrar
from st2common.exceptions.apivalidation import ValueValidationException
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.rbac.types import PermissionType
from st2common.rbac.backends import get_rbac_backend
from st2common.router import abort
from st2common.services import packs as packs_service
from st2common.models.api.pack import ConfigAPI
from st2common.persistence.pack import Config

http_client = six.moves.http_client

__all__ = [
    'PackConfigsController'
]

LOG = logging.getLogger(__name__)


class PackConfigsController(ResourceController, BaseRestControllerMixin):
    model = ConfigAPI
    access = Config
    supported_filters = {}

    def __init__(self):
        super(PackConfigsController, self).__init__()

        # Note: This method is used to retrieve object for RBAC purposes and in
        # this case, RBAC is checked on the parent PackDB object
        self.get_one_db_method = packs_service.get_pack_by_ref

    def get_all(self, requester_user, sort=None, offset=0, limit=None, show_secrets=False,
                **raw_filters):
        """
        Retrieve configs for all the packs.

        Handles requests:
            GET /configs/
        """
        from_model_kwargs = {
            'mask_secrets': self._get_mask_secrets(requester_user, show_secrets=show_secrets)
        }
        return super(PackConfigsController, self)._get_all(sort=sort,
                                                           offset=offset,
                                                           limit=limit,
                                                           from_model_kwargs=from_model_kwargs,
                                                           raw_filters=raw_filters,
                                                           requester_user=requester_user)

    def get_one(self, pack_ref, requester_user, show_secrets=False):
        """
        Retrieve config for a particular pack.

        Handles requests:
            GET /configs/<pack_ref>
        """
        from_model_kwargs = {
            'mask_secrets': self._get_mask_secrets(requester_user, show_secrets=show_secrets)
        }
        try:
            instance = packs_service.get_pack_by_ref(pack_ref=pack_ref)
        except StackStormDBObjectNotFoundError:
            msg = 'Unable to identify resource with pack_ref "%s".' % (pack_ref)
            abort(http_client.NOT_FOUND, msg)

        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=instance,
                                                          permission_type=PermissionType.PACK_VIEW)

        return self._get_one_by_pack_ref(pack_ref=pack_ref, from_model_kwargs=from_model_kwargs)

    def put(self, pack_config_content, pack_ref, requester_user, show_secrets=False):
        """
            Create a new config for a pack.

            Handles requests:
                POST /configs/<pack_ref>
        """

        try:
            config_api = ConfigAPI(pack=pack_ref, values=vars(pack_config_content))
            config_api.validate(validate_against_schema=True)
        except jsonschema.ValidationError as e:
            raise ValueValidationException(six.text_type(e))

        self._dump_config_to_disk(config_api)

        config_db = ConfigsRegistrar.save_model(config_api)

        mask_secrets = self._get_mask_secrets(requester_user, show_secrets=show_secrets)
        return ConfigAPI.from_model(config_db, mask_secrets=mask_secrets)

    def _dump_config_to_disk(self, config_api):
        config_content = yaml.safe_dump(config_api.values, default_flow_style=False)

        configs_path = os.path.join(cfg.CONF.system.base_path, 'configs/')
        config_path = os.path.join(configs_path, '%s.yaml' % config_api.pack)
        with open(config_path, 'w') as f:
            f.write(config_content)


pack_configs_controller = PackConfigsController()
