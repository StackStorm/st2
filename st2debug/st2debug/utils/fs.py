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
import glob
import shutil

__all__ = [
    'get_full_file_list',
    'get_dirs_in_path',
    'copy_files',
    'remove_file'
]


def get_full_file_list(file_path_glob):
    """
    Return a list of absolute file paths to all the files in the provided file
    path glob.

    :type file_path_glob: ``str``
    """
    file_list = []

    for file_name in glob.glob(file_path_glob):
        full_file_path = os.path.abspath(file_name)
        file_list.append(full_file_path)

    return file_list


def get_dirs_in_path(file_path):
    """
    Retrieve full paths to the directories in the provided file path.

    :param file_path: Parent directory file path.
    :type file_path: ``str``

    :rtype: ``list``
    """
    names = os.listdir(file_path)

    result = []
    for name in names:
        full_path = os.path.join(file_path, name)

        if not os.path.isdir(full_path):
            continue

        result.append(full_path)
    return result


def copy_files(file_paths, destination, ignore_errors=True):
    """
    Copy files to the provided destination.

    :type file_paths: ``list``
    :type destination: ``str``

    :param ignore_errors: True to ignore errors if a source or destination doesnt'e exist.
    :type ignore_errors: ``bool``
    """

    for file_path in file_paths:
        try:
            shutil.copy(src=file_path, dst=destination)
        except IOError as e:
            if not ignore_errors:
                raise e

    return True


def remove_file(file_path, ignore_errors=True):
    try:
        os.remove(file_path)
    except Exception as e:
        if not ignore_errors:
            raise e


def remove_dir(dir_path, ignore_errors=True):
    """
    Recursively remove a directory.

    :param dir_path: Directory to be removed.
    :type dir_path: ``str``

    :param ignore_errors: True to ignore errors during removal.
    :type ignore_errors: ``bool``
    """
    try:
        shutil.rmtree(dir_path, ignore_errors)
    except Exception as e:
        if not ignore_errors:
            raise e
