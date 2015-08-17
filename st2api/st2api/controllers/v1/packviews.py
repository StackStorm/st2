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
from st2common.content.utils import get_pack_file_abs_path
from st2common.rbac.types import PermissionType
from st2common.rbac.decorators import request_user_has_permission
from st2common.rbac.decorators import request_user_has_resource_permission

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class BaseFileController(resource.ResourceController):
    model = PackAPI
    access = Pack

    supported_filters = {}

    @jsexpose()
    def get_all(self, **kwargs):
        return abort(404)

    def _get_file_content(self, file_path):
        with open(file_path, 'r') as fp:
            content = fp.read()

        return content


class FilesController(BaseFileController):
    """
    Controller which allows user to retrieve content of all the files inside the pack.
    """

    @request_user_has_resource_permission(permission_type=PermissionType.PACK_VIEW)
    @jsexpose(arg_types=[str], status_code=http_client.OK)
    def get_one(self, name_or_id):
        """
            Outputs the content of all the files inside the pack.

            Handles requests:
                GET /packs/views/files/<pack_name>
        """
        pack_db = self._get_by_name_or_id(name_or_id=name_or_id)
        pack_name = pack_db.name
        pack_files = pack_db.files

        result = []
        for file_path in pack_files:
            normalized_file_path = get_pack_file_abs_path(pack_name=pack_name, file_path=file_path)

            if not normalized_file_path or not os.path.isfile(normalized_file_path):
                # Ignore references to files which don't exist on disk
                continue

            content = self._get_file_content(file_path=normalized_file_path)
            item = {
                'file_path': file_path,
                'content': content
            }
            result.append(item)

        return result


class FileController(BaseFileController):
    """
    Controller which allows user to retrieve content of a specific file in a pack.
    """

    @request_user_has_resource_permission(permission_type=PermissionType.PACK_VIEW)
    @jsexpose(content_type='text/plain', status_code=http_client.OK)
    def get_one(self, name_or_id, *file_path_components):
        """
            Outputs the content of all the files inside the pack.

            Handles requests:
                GET /packs/views/files/<pack_name>/<file path>
        """
        pack_db = self._get_by_name_or_id(name_or_id=name_or_id)

        if not file_path_components:
            raise ValueError('Missing file path')

        file_path = os.path.join(*file_path_components)
        pack_name = pack_db.name

        normalized_file_path = get_pack_file_abs_path(pack_name=pack_name, file_path=file_path)

        if not normalized_file_path or not os.path.isfile(normalized_file_path):
            # Ignore references to files which don't exist on disk
            raise StackStormDBObjectNotFoundError('File "%s" not found' % (file_path))

        content = self._get_file_content(file_path=normalized_file_path)
        return content


class PackViewsController(RestController):
    files = FilesController()
    file = FileController()
