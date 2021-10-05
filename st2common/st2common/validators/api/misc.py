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
from st2common.constants.pack import SYSTEM_PACK_NAME
from st2common.exceptions.apivalidation import ValueValidationException

__all__ = ["validate_not_part_of_system_pack"]


def validate_not_part_of_system_pack(resource_db):
    """
    Validate that the provided resource database object doesn't belong to
    a system level pack.

    If it does, ValueValidationException is thrown.

    :param resource_db: Resource database object to check.
    :type resource_db: ``object``
    """
    pack = getattr(resource_db, "pack", None)

    if pack == SYSTEM_PACK_NAME:
        msg = "Resources belonging to system level packs can't be manipulated"
        raise ValueValidationException(msg)

    return resource_db
