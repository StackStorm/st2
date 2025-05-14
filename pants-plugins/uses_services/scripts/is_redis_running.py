# Copyright 2023 The StackStorm Authors.
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

import sys


def _is_redis_running(coord_url: str) -> bool:
    """Connect to redis with connection logic that mirrors the st2 code.

    In particular, this is based on:
      - st2common.services.coordination.coordinator_setup()

    This should not import the st2 code as it should be self-contained.
    """
    # late import so that __file__ can be imported in the pants plugin without these imports
    from tooz import ToozError, coordination

    member_id = "pants-uses_services-redis"
    coordinator = coordination.get_coordinator(coord_url, member_id)
    try:
        coordinator.start(start_heart=False)
    except ToozError:
        return False
    return True


if __name__ == "__main__":
    args = dict((k, v) for k, v in enumerate(sys.argv))

    # unit and integration tests require a coordinator, and mostly use this redis url.
    # In some cases, unit tests can also use an in-memory coordinator: "zake://"
    coord_url = args.get(1, "redis://127.0.0.1:6379?namespace=_st2_test")

    is_running = _is_redis_running(coord_url)
    exit_code = 0 if is_running else 1
    sys.exit(exit_code)
