#!/usr/bin/env python

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
import sys

from st2actions.scheduler import config
from st2actions.scheduler import handler as scheduler_handler
from st2common.service_setup import db_setup
from st2common.service_setup import db_teardown


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
LOG = logging.getLogger()


def main():
    config.parse_args()

    # Connect to db.
    db_setup()

    try:
        handler = scheduler_handler.get_handler()
        handler._cleanup_policy_delayed()
        LOG.info(
            "SUCCESS: Completed clean up of executions with deprecated policy-delayed status."
        )
        exit_code = 0
    except Exception as e:
        LOG.error(
            "ABORTED: Clean up of executions with deprecated policy-delayed status aborted on "
            "first failure. %s" % e.message  # pylint: disable=no-member
        )
        exit_code = 1

    # Disconnect from db.
    db_teardown()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
