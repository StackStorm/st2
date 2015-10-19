#!/usr/bin/env python
# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A migration script that cleans up old queues.
"""

import traceback

from kombu import Connection
from st2common import config
from st2common.transport import reactor
from st2common.transport import utils as transport_utils


class Migrate_0_13_x_to_1_1_0(object):
    """
    Handles migration of messaging setup from 0.13.x to 1.1.
    """

    # All these queues are either not required due to name
    # changes or changes in durability proeprties.
    OLD_QS = [
        # Name changed in 1.1
        reactor.get_trigger_cud_queue('st2.trigger.watch.timers', routing_key='#'),
        # Split to multiple queues in 1.1
        reactor.get_trigger_cud_queue('st2.trigger.watch.sensorwrapper', routing_key='#'),
        # Name changed in 1.1
        reactor.get_trigger_cud_queue('st2.trigger.watch.webhooks', routing_key='#')
    ]

    def migrate(self):
        self._cleanup_old_queues()

    def _cleanup_old_queues(self):
        with Connection(transport_utils.get_messaging_urls()) as connection:
            for q in self.OLD_QS:
                bound_q = q(connection.default_channel)
                try:
                    bound_q.delete()
                except:
                    print('Failed to delete %s.' % q.name)
                    traceback.print_exc()


def main():
    try:
        migrator = Migrate_0_13_x_to_1_1_0()
        migrator.migrate()
    except:
        print('Messaging setup migration failed.')
        traceback.print_exc()


if __name__ == '__main__':
    config.parse_args(args={})
    main()
