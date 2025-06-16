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

import socket
import sys

from contextlib import closing


def _is_st2cluster_running(endpoints: list[tuple[str, str]]) -> bool:
    """Check for listening ports of st2auth, st2api, and st2stream services.

    This should not import the st2 code as it should be self-contained.
    """
    # TODO: Once each service gains a reliable health check endpoint, use that.
    # https://github.com/StackStorm/st2/issues/4020
    for host, port in endpoints:
        # based on https://stackoverflow.com/a/35370008/1134951
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            # errno=0 means the connection succeeded
            if sock.connect_ex((host, int(port))) != 0:
                # failed to create a connection to the port.
                return False
    return True


if __name__ == "__main__":
    args_iter = iter(sys.argv[1:])
    # Turn the list into 2 tuples (zip with query the same iterator twice for each entry)
    endpoints = list(zip(args_iter, args_iter))
    if not endpoints:
        endpoints = [
            ("127.0.0.1", "9100"),
            ("127.0.0.1", "9101"),
            ("127.0.0.1", "9102"),
        ]

    is_running = _is_st2cluster_running(endpoints)
    exit_code = 0 if is_running else 1
    sys.exit(exit_code)
