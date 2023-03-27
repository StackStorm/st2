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


def _is_rabbitmq_running(mq_urls: list[str]) -> bool:
    """Connect to rabbitmq with connection logic that mirrors the st2 code.

    In particular, this is based on:
      - st2common.transport.utils.get_connection()
      - st2common.transport.bootstrap_utils.register_exchanges()

    This should not import the st2 code as it should be self-contained.
    """
    # late import so that __file__ can be imported in the pants plugin without these imports
    from kombu import Connection

    with Connection(mq_urls) as connection:
        try:
            # connection is lazy. Make it connect immediately.
            connection.connect()
        except connection.connection_errors:
            return False
    return True


if __name__ == "__main__":
    mq_urls = list(sys.argv[1:])
    if not mq_urls:
        # st2.tests*.conf ends in /, but the default ends in //
        mq_urls = ["amqp://guest:guest@127.0.0.1:5672//"]

    is_running = _is_rabbitmq_running(mq_urls)
    exit_code = 0 if is_running else 1
    sys.exit(exit_code)
