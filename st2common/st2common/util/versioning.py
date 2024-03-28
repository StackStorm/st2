# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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

from __future__ import absolute_import

import sys

import semver

from st2common import __version__ as stackstorm_version

__all__ = ["get_stackstorm_version", "get_python_version", "complex_semver_match"]


def get_stackstorm_version():
    """
    Return a valid semver version string for the currently running StackStorm version.
    """
    # Special handling for dev versions which are not valid semver identifiers
    if "dev" in stackstorm_version and stackstorm_version.count(".") == 1:
        version = stackstorm_version.replace("dev", ".0")
        return version

    return stackstorm_version


def get_python_version():
    """
    Return Python version used by this installation.
    """
    version_info = sys.version_info
    return "%s.%s.%s" % (version_info.major, version_info.minor, version_info.micro)


def complex_semver_match(version, version_specifier):
    """
    Custom semver match function which also supports complex semver specifiers
    such as >=1.6, <2.0, etc.

    NOTE: This function also supports special "all" version specifier. When "all"
    is specified, any version provided will be considered valid.

    :rtype: ``bool``
    """
    if version_specifier == "all":
        return True

    split_version_specifier = version_specifier.split(",")

    if len(split_version_specifier) == 1:
        # No comma, we can do a simple comparision
        return semver.Version.parse(version).match(version_specifier)
    else:
        # Compare part by part
        for version_specifier_part in split_version_specifier:
            version_specifier_part = version_specifier_part.strip()

            if not version_specifier_part:
                continue

            if not semver.Version.parse(version).match(version_specifier_part):
                return False

        return True
