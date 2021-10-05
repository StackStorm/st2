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

from __future__ import absolute_import
import os
from pkg_resources import get_distribution

from st2common.constants.pack import USER_PACK_NAME_BLACKLIST

__all__ = ["RequirementsValidator", "validate_pack_name"]


class RequirementsValidator(object):
    @staticmethod
    def validate(requirements_file):
        if not os.path.exists(requirements_file):
            raise Exception("Requirements file %s not found." % requirements_file)
        missing = []
        with open(requirements_file, "r") as f:
            for line in f:
                rqmnt = line.strip()
                try:
                    get_distribution(rqmnt)
                except:
                    missing.append(rqmnt)
        return missing


def validate_pack_name(name):
    """
    Validate the content pack name.

    Throws Exception on invalid name.

    :param name: Content pack name to validate.
    :type name: ``str``

    :rtype: ``str``
    """
    if not name:
        raise ValueError("Content pack name cannot be empty")

    if name.lower() in USER_PACK_NAME_BLACKLIST:
        raise ValueError('Name "%s" is blacklisted and can\'t be used' % (name.lower()))

    return name
