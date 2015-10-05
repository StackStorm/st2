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
from six.moves import http_client

from st2common import log as logging
from st2common.models.api.base import jsexpose
from st2api.controllers.resource import ResourceController
from st2common.models.api.pack import PackAPI
from st2common.persistence.pack import Pack
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_db_permission

__all__ = [
    'PacksController',
    'BasePacksController'
]

LOG = logging.getLogger(__name__)


class BasePacksController(ResourceController):
    model = PackAPI
    access = Pack

    def _get_one_by_ref_or_id(self, ref_or_id, exclude_fields=None):
        LOG.info('GET %s with ref_or_id=%s', pecan.request.path, ref_or_id)

        instance = self._get_by_ref_or_id(ref_or_id=ref_or_id, exclude_fields=exclude_fields)

        if not instance:
            msg = 'Unable to identify resource with ref_or_id "%s".' % (ref_or_id)
            pecan.abort(http_client.NOT_FOUND, msg)
            return

        from_model_kwargs = self._get_from_model_kwargs_for_request(request=pecan.request)
        result = self.model.from_model(instance, **from_model_kwargs)
        LOG.debug('GET %s with ref_or_id=%s, client_result=%s', pecan.request.path, ref_or_id,
                  result)

        return result

    def _get_by_ref_or_id(self, ref_or_id, exclude_fields=None):
        resource_db = self._get_by_id(resource_id=ref_or_id, exclude_fields=exclude_fields)

        if not resource_db:
            # Try ref
            resource_db = self._get_by_ref(ref=ref_or_id, exclude_fields=exclude_fields)

        return resource_db

    def _get_by_ref(self, ref, exclude_fields=None):
        """
        Note: In this case "ref" is pack name and not StackStorm's ResourceReference.
        """
        resource_db = self.access.query(ref=ref, exclude_fields=exclude_fields).first()
        return resource_db


class PacksController(BasePacksController):
    from st2api.controllers.v1.packviews import PackViewsController

    model = PackAPI
    access = Pack
    supported_filters = {
        'name': 'name',
        'ref': 'ref'
    }

    query_options = {
        'sort': ['ref']
    }

    # Nested controllers
    views = PackViewsController()

    @request_user_has_permission(permission_type=PermissionType.PACK_VIEW)
    @jsexpose()
    def get_all(self, **kwargs):
        return super(PacksController, self)._get_all(**kwargs)

    @request_user_has_resource_db_permission(permission_type=PermissionType.PACK_VIEW)
    @jsexpose(arg_types=[str])
    def get_one(self, ref_or_id):
        return self._get_one_by_ref_or_id(ref_or_id=ref_or_id)
