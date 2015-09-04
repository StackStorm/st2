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

"""
File system related utility functions.
"""

import os
import os.path
import fnmatch

__all__ = [
    'get_file_list'
]


def get_file_list(directory, exclude_patterns=None):
    """
    Recurisvely retrieve a list of files in the provided directory.

    :param directory: Path to directory to retrieve the file list for.
    :type directory: ``str``

    :param exclude_patterns: A list of `fnmatch` compatible patterns of files to exclude from
                             the result.
     :type exclude_patterns: ``list``

    :return: List of files in the provided directory. Each file path is relative
             to the provided directory.
    :rtype: ``list``
    """
    result = []
    if not directory.endswith('/'):
        # Make sure trailing slash is present
        directory = directory + '/'

    def include_file(file_path):
        if not exclude_patterns:
            return True

        for exclude_pattern in exclude_patterns:
            if fnmatch.fnmatch(file_path, exclude_pattern):
                return False

        return True

    for (dirpath, dirnames, filenames) in os.walk(directory):
        base_path = dirpath.replace(directory, '')

        for filename in filenames:
            if base_path:
                file_path = os.path.join(base_path, filename)
            else:
                file_path = filename

            if include_file(file_path=file_path):
                result.append(file_path)

    return result
