# Copyright 2024 The StackStorm Authors.
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
from __future__ import annotations

import os
import pwd
import sys


def _has_system_user(system_user: str) -> bool:
    """Make sure the system_user exists.

    This should not import the st2 code as it should be self-contained.
    """
    try:
        pwd.getpwnam(system_user)
    except KeyError:
        # put current user (for use in error msg instructions)
        print(pwd.getpwuid(os.getuid()).pw_name)
        return False
    print(system_user)
    return True


if __name__ == "__main__":
    args = dict((k, v) for k, v in enumerate(sys.argv))

    system_user = args.get(1, "stanley")

    is_running = _has_system_user(system_user)
    exit_code = 0 if is_running else 1
    sys.exit(exit_code)
