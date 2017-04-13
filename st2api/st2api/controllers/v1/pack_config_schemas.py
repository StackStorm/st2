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

from st2api.controllers.resource import ResourceController
from st2api.controllers.v1.packs import packs_controller
from st2common.services import packs as packs_service
from st2common.models.api.pack import ConfigSchemaAPI
from st2common.persistence.pack import ConfigSchema

http_client = six.moves.http_client

__all__ = [
    'PackConfigSchemasController'
]


class PackConfigSchemasController(ResourceController):
    model = ConfigSchemaAPI
    access = ConfigSchema
    supported_filters = {}

    def __init__(self):
        super(PackConfigSchemasController, self).__init__()

        # Note: This method is used to retrieve object for RBAC purposes and in
        # this case, RBAC is checked on the parent PackDB object
        self.get_one_db_method = packs_service.get_pack_by_ref

    def get_all(self, sort=None, offset=0, limit=None, **raw_filters):
        """
        Retrieve config schema for all the packs.

        Handles requests:
            GET /config_schema/
        """

        return super(PackConfigSchemasController, self)._get_all(sort=sort,
                                                                 offset=offset,
                                                                 limit=limit,
                                                                 raw_filters=raw_filters)

    def get_one(self, pack_ref, requester_user):
        """
        Retrieve config schema for a particular pack.

        Handles requests:
            GET /config_schema/<pack_ref>
        """
        packs_controller._get_one_by_ref_or_id(ref_or_id=pack_ref, requester_user=requester_user)

        return self._get_one_by_pack_ref(pack_ref=pack_ref)


pack_config_schema_controller = PackConfigSchemasController()
