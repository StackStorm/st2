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
Auth backend related constants.
"""

from st2common.util.enum import Enum

__all__ = ["AuthBackendCapability"]


class AuthBackendCapability(Enum):
    # This auth backend can authenticate a user.
    CAN_AUTHENTICATE_USER = "can_authenticate_user"

    # Auth backend can provide additional information about a particular user.
    HAS_USER_INFORMATION = "has_user_info"

    # Auth backend can provide a group membership information for a particular user.
    HAS_GROUP_INFORMATION = "has_groups_info"
