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
Module containing various versioning utils.
"""

import semver

from st2common import __version__ as stackstorm_version

__all__ = [
    'get_stackstorm_version',

    'complex_semver_match'
]


def get_stackstorm_version():
    """
    Return a valid semver version string for the currently running StackStorm version.
    """
    # Special handling for dev versions which are not valid semver identifiers
    if 'dev' in stackstorm_version and stackstorm_version.count('.') == 1:
        version = stackstorm_version.replace('dev', '.0')
        return version

    return stackstorm_version


def complex_semver_match(version, version_specifier):
    """
    Custom semver match function which also supports complex semver specifiers
    such as >=1.6, <2.0, etc.

    :rtype: ``bool``
    """
    split_version_specifier = version_specifier.split(',')

    if len(split_version_specifier) == 1:
        # No comma, we can do a simple comparision
        return semver.match(version, version_specifier)
    else:
        # Compare part by part
        for version_specifier_part in split_version_specifier:
            version_specifier_part = version_specifier_part.strip()

            if not version_specifier_part:
                continue

            if not semver.match(version, version_specifier_part):
                return False

        return True
