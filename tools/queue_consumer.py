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

"""
A utility script which listens on queue for messages and prints them to stdout.
"""

from __future__ import absolute_import

import random
import argparse
from pprint import pprint

from kombu.mixins import ConsumerMixin
from kombu import Exchange, Queue

from st2common import config
from st2common.transport import utils as transport_utils


class QueueConsumer(ConsumerMixin):
    def __init__(self, connection, queue):
        self.connection = connection
        self.queue = queue

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(
                queues=[self.queue], accept=["pickle"], callbacks=[self.process_task]
            )
        ]

    def process_task(self, body, message):
        print("===================================================")
        print("Received message")
        print("message.properties:")
        pprint(message.properties)
        print("message.delivery_info:")
        pprint(message.delivery_info)
        print("body:")
        pprint(body)
        print("===================================================")

        message.ack()


def main(queue, exchange, routing_key="#"):
    exchange = Exchange(exchange, type="topic")
    queue = Queue(
        name=queue, exchange=exchange, routing_key=routing_key, auto_delete=True
    )

    with transport_utils.get_connection() as connection:
        connection.connect()
        watcher = QueueConsumer(connection=connection, queue=queue)
        watcher.run()


if __name__ == "__main__":
    config.parse_args(args={})
    parser = argparse.ArgumentParser(description="Queue consumer")
    parser.add_argument("--exchange", required=True, help="Exchange to listen on")
    parser.add_argument("--routing-key", default="#", help="Routing key")
    args = parser.parse_args()

    queue_name = args.exchange + str(random.randint(1, 10000))
    main(queue=queue_name, exchange=args.exchange, routing_key=args.routing_key)
