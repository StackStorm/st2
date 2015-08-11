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

from st2common.models.api.base import jsexpose
from st2api.controllers.resource import ResourceController
from st2common.models.api.pack import PackAPI
from st2common.persistence.pack import Pack
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_permission

__all__ = [
    'PacksController'
]


class PacksController(ResourceController):
    model = PackAPI
    access = Pack
    supported_filters = {
        'name': 'name',
        'ref': 'ref'
    }

    query_options = {
        'sort': ['ref']
    }

    @jsexpose()
    @request_user_has_permission(permission_type=PermissionType.PACK_VIEW)
    def get_all(self, **kwargs):
        return super(PacksController, self).get_all(**kwargs)

    @jsexpose(arg_types=[str])
    @request_user_has_resource_permission(permission_type=PermissionType.PACK_VIEW)
    def get_one(self, name_or_id):
        return self._get_one_by_name_or_id(name_or_id=name_or_id)
