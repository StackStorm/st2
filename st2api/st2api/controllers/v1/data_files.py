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
import os.path

import six

from st2common import log as logging
from st2common.constants.triggers import ACTION_FILE_WRITTEN_TRIGGER
from st2common.persistence.pack import Pack
from st2common.content.utils import get_pack_base_path
from st2common.content.utils import get_pack_file_abs_path
from st2common.content.utils import get_pack_resource_file_abs_path
from st2common.content.utils import get_relative_path_to_pack
from st2common.util.system_info import get_host_info


__all__ = [
    'BaseDataFilesController'
]

http_client = six.moves.http_client

LOG = logging.getLogger(__name__)


class BaseDataFilesController(object):
    """
    Base controller for writting raw files to disk.
    """

    def _handle_data_files(self, pack_ref, data_files, resource_type=None):
        """
        Method for handling action data files.

        This method performs two tasks:

        1. Writes files to disk
        2. Updates affected PackDB model
        """
        # Write files to disk
        written_file_paths = self._write_data_files_to_disk(pack_ref=pack_ref,
                                                            data_files=data_files,
                                                            resource_type=resource_type)

        # Update affected PackDB model (update a list of files) Update PackDB
        pack_db = self._update_pack_model(pack_ref=pack_ref, data_files=data_files,
                                          written_file_paths=written_file_paths)

        return written_file_paths, pack_db

    def _write_data_files_to_disk(self, pack_ref, data_files, resource_type=None):
        """
        Write files to disk.
        """
        written_file_paths = []

        for data_file in data_files:
            file_path = data_file['file_path']
            content = data_file['content']

            if resource_type:
                file_path = get_pack_resource_file_abs_path(pack_ref=pack_ref,
                                                            resource_type=resource_type,
                                                            file_path=file_path)
            else:
                file_path = get_pack_file_abs_path(pack_ref=pack_ref,
                                                   file_path=file_path)

            LOG.debug('Writing data file "%s" to "%s"' % (str(data_file), file_path))
            self._write_data_file(pack_ref=pack_ref, file_path=file_path, content=content)
            written_file_paths.append(file_path)

        return written_file_paths

    def _write_data_file(self, pack_ref, file_path, content):
        """
        Write data file on disk.
        """
        # Throw if pack directory doesn't exist
        pack_base_path = get_pack_base_path(pack_name=pack_ref)
        if not os.path.isdir(pack_base_path):
            raise ValueError('Directory for pack "%s" doesn\'t exist' % (pack_ref))

        # Create pack sub-directory tree if it doesn't exist
        directory = os.path.dirname(file_path)

        if not os.path.isdir(directory):
            os.makedirs(directory)

        with open(file_path, 'w') as fp:
            fp.write(content)

    def _dispatch_trigger_for_written_data_files(self, action_db, written_data_files):
        trigger = ACTION_FILE_WRITTEN_TRIGGER['name']
        host_info = get_host_info()

        for file_path in written_data_files:
            payload = {
                'ref': action_db.ref,
                'file_path': file_path,
                'host_info': host_info
            }
            self._trigger_dispatcher.dispatch(trigger=trigger, payload=payload)

    def _update_pack_model(self, pack_ref, data_files, written_file_paths):
        """
        Update PackDB models (update files list).
        """
        file_paths = []  # A list of paths relative to the pack directory for new files
        for file_path in written_file_paths:
            file_path = get_relative_path_to_pack(pack_ref=pack_ref, file_path=file_path)
            file_paths.append(file_path)

        pack_db = Pack.get_by_ref(pack_ref)
        pack_db.files = set(pack_db.files)
        pack_db.files.update(set(file_paths))
        pack_db.files = sorted(list(pack_db.files))
        pack_db = Pack.add_or_update(pack_db)

        return pack_db
