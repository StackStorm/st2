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
import logging
import st2common.config as config

from st2common.transport.bootstrap_utils import register_exchanges_with_retry


def _setup():
    config.parse_args()

    # 2. setup logging.
    logging.basicConfig(
        format="%(asctime)s %(levelname)s [-] %(message)s", level=logging.DEBUG
    )


def main():
    _setup()
    register_exchanges_with_retry()


# The scripts sets up Exchanges in RabbitMQ.
if __name__ == "__main__":
    main()
