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

import codecs
import mimetypes
import os

import six
from wsgiref.handlers import format_date_time

from st2api.controllers.v1.packs import BasePacksController
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common import log as logging
from st2common.models.api.pack import PackAPI
from st2common.persistence.pack import Pack
from st2common.content.utils import get_pack_file_abs_path
from st2common.rbac.types import PermissionType
from st2common.rbac.backends import get_rbac_backend
from st2common.router import abort
from st2common.router import Response

http_client = six.moves.http_client

__all__ = [
    'FilesController',
    'FileController'
]

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)

BOM_LEN = len(codecs.BOM_UTF8)

# Maximum file size in bytes. If the file on disk is larger then this value, we don't include it
# in the response. This prevents DDoS / exhaustion attacks.
MAX_FILE_SIZE = (500 * 1000)

# File paths in the file controller for which RBAC checks are not performed
WHITELISTED_FILE_PATHS = [
    'icon.png'
]


class BaseFileController(BasePacksController):
    model = PackAPI
    access = Pack

    supported_filters = {}
    query_options = {}

    def get_all(self):
        return abort(404)

    def _get_file_size(self, file_path):
        return self._get_file_stats(file_path=file_path)[0]

    def _get_file_stats(self, file_path):
        try:
            file_stats = os.stat(file_path)
        except OSError:
            return (None, None)

        return file_stats.st_size, file_stats.st_mtime

    def _get_file_content(self, file_path):
        with codecs.open(file_path, 'rb') as fp:
            content = fp.read()

        return content

    def _process_file_content(self, content):
        """
        This method processes the file content and removes unicode BOM character if one is present.

        Note: If we don't do that, files view explodes with "UnicodeDecodeError: ... invalid start
        byte" because the json.dump doesn't know how to handle BOM character.
        """
        if content.startswith(codecs.BOM_UTF8):
            content = content[BOM_LEN:]

        return content


class FilesController(BaseFileController):
    """
    Controller which allows user to retrieve content of all the files inside the pack.
    """

    def __init__(self):
        super(FilesController, self).__init__()
        self.get_one_db_method = self._get_by_ref_or_id

    def get_one(self, ref_or_id, requester_user):
        """
            Outputs the content of all the files inside the pack.

            Handles requests:
                GET /packs/views/files/<pack_ref_or_id>
        """
        pack_db = self._get_by_ref_or_id(ref_or_id=ref_or_id)

        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=pack_db,
                                                          permission_type=PermissionType.PACK_VIEW)

        if not pack_db:
            msg = 'Pack with ref_or_id "%s" does not exist' % (ref_or_id)
            raise StackStormDBObjectNotFoundError(msg)

        pack_ref = pack_db.ref
        pack_files = pack_db.files

        result = []
        for file_path in pack_files:
            normalized_file_path = get_pack_file_abs_path(pack_ref=pack_ref, file_path=file_path)
            if not normalized_file_path or not os.path.isfile(normalized_file_path):
                # Ignore references to files which don't exist on disk
                continue

            file_size = self._get_file_size(file_path=normalized_file_path)
            if file_size is not None and file_size > MAX_FILE_SIZE:
                LOG.debug('Skipping file "%s" which size exceeds max file size (%s bytes)' %
                          (normalized_file_path, MAX_FILE_SIZE))
                continue

            content = self._get_file_content(file_path=normalized_file_path)

            include_file = self._include_file(file_path=file_path, content=content)
            if not include_file:
                LOG.debug('Skipping binary file "%s"' % (normalized_file_path))
                continue

            item = {
                'file_path': file_path,
                'content': content
            }
            result.append(item)
        return result

    def _include_file(self, file_path, content):
        """
        Method which returns True if the following file content should be included in the response.

        Right now we exclude any file with UTF8 BOM character in it - those are most likely binary
        files such as icon, etc.
        """
        if codecs.BOM_UTF8 in content[:1024]:
            return False

        if b"\0" in content[:1024]:
            # Found null byte, most likely a binary file
            return False

        return True


class FileController(BaseFileController):
    """
    Controller which allows user to retrieve content of a specific file in a pack.
    """

    def get_one(self, ref_or_id, file_path, requester_user, if_none_match=None,
                if_modified_since=None):
        """
            Outputs the content of a specific file in a pack.

            Handles requests:
                GET /packs/views/file/<pack_ref_or_id>/<file path>
        """
        pack_db = self._get_by_ref_or_id(ref_or_id=ref_or_id)

        if not pack_db:
            msg = 'Pack with ref_or_id "%s" does not exist' % (ref_or_id)
            raise StackStormDBObjectNotFoundError(msg)

        if not file_path:
            raise ValueError('Missing file path')

        pack_ref = pack_db.ref

        # Note: Until list filtering is in place we don't require RBAC check for icon file
        permission_type = PermissionType.PACK_VIEW
        if file_path not in WHITELISTED_FILE_PATHS:
            rbac_utils = get_rbac_backend().get_utils_class()
            rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                              resource_db=pack_db,
                                                              permission_type=permission_type)

        normalized_file_path = get_pack_file_abs_path(pack_ref=pack_ref, file_path=file_path)
        if not normalized_file_path or not os.path.isfile(normalized_file_path):
            # Ignore references to files which don't exist on disk
            raise StackStormDBObjectNotFoundError('File "%s" not found' % (file_path))

        file_size, file_mtime = self._get_file_stats(file_path=normalized_file_path)

        response = Response()

        if not self._is_file_changed(file_mtime,
                                     if_none_match=if_none_match,
                                     if_modified_since=if_modified_since):
            response.status = http_client.NOT_MODIFIED
        else:
            if file_size is not None and file_size > MAX_FILE_SIZE:
                msg = ('File %s exceeds maximum allowed file size (%s bytes)' %
                       (file_path, MAX_FILE_SIZE))
                raise ValueError(msg)

            content_type = mimetypes.guess_type(normalized_file_path)[0] or \
                'application/octet-stream'

            response.headers['Content-Type'] = content_type
            response.body = self._get_file_content(file_path=normalized_file_path)

        response.headers['Last-Modified'] = format_date_time(file_mtime)
        response.headers['ETag'] = repr(file_mtime)

        return response

    def _is_file_changed(self, file_mtime, if_none_match=None, if_modified_since=None):
        # For if_none_match check against what would be the ETAG value
        if if_none_match:
            return repr(file_mtime) != if_none_match

        # For if_modified_since check against file_mtime
        if if_modified_since:
            return if_modified_since != format_date_time(file_mtime)

        # Neither header is provided therefore assume file is changed.
        return True


class PackViewsController(object):
    files = FilesController()
    file = FileController()
