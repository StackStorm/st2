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
from pecan import abort
from pecan.rest import RestController

from st2api.controllers import resource
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common import log as logging
from st2common.models.api.base import jsexpose
from st2common.models.api.pack import PackAPI
from st2common.persistence.pack import Pack
from st2common.content.utils import get_pack_resource_file_abs_path

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class FilesController(resource.ResourceController):
    """
    Controller which allows user to retrieve content of a particular file in the provided pack.
    """

    model = PackAPI
    access = Pack

    supported_filters = {}

    @jsexpose()
    def get_all(self, **kwargs):
        return abort(404)

    @jsexpose(arg_types=[str, str, str], content_type='text/plain', status_code=http_client.OK)
    def get_one(self, name_or_id, resource_type, file_path):
        """
            Outputs the content of the requested file.

            Handles requests:
                GET /packs/views/files/<pack_name>/<resource_type>/<file path>
        """
        pack_db = self._get_by_name_or_id(name_or_id=name_or_id)
        pack_name = pack_db.name
        file_path = get_pack_resource_file_abs_path(pack_name=pack_name,
                                                    resource_type=resource_type,
                                                    file_path=file_path)

        if not file_path or not os.path.isfile(file_path):
            raise StackStormDBObjectNotFoundError('File "%s" not found' % (file_path))

        with open(file_path) as fp:
            content = fp.read()

        return content


class PackViewsController(RestController):
    files = FilesController()
