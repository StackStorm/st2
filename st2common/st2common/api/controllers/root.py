# -*- coding: utf-8 -*-
#
# Copyright 2013 - Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import pecan
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from stackstorm.openstack.common import log as logging
from stackstorm.api.controllers import resource
from stackstorm.api.controllers.v1 import root as v1_root

LOG = logging.getLogger(__name__)

API_STATUS = wtypes.Enum(str, 'SUPPORTED', 'CURRENT', 'DEPRECATED')


class APIVersion(resource.Resource):
    """API Version."""

    id = wtypes.text
    status = API_STATUS
    link = resource.Link


class RootController(object):

    v1 = v1_root.Controller()

    @wsme_pecan.wsexpose([APIVersion])
    def index(self):
        LOG.debug("Fetching API versions.")

        host_url = '%s/%s' % (pecan.request.host_url, 'v1')
        api_v1 = APIVersion(id='v1.0',
                            status='CURRENT',
                            link=resource.Link(href=host_url, target='v1'))

        return [api_v1]
