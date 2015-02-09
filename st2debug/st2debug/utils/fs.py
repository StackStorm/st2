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
    'copy_files'
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


def copy_files(file_paths, destination):
    """
    Copy files to the provided destination.

    :type file_paths: ``list``
    :type destination: ``str``
    """

    for file_path in file_paths:
        shutil.copy(src=file_path, dst=destination)

    return True
