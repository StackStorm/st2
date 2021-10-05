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
A utility script which sends test messages to a queue.
"""

from __future__ import absolute_import

import argparse

import eventlet
from kombu import Exchange

from st2common import config
from st2common.transport.publishers import PoolPublisher


def main(exchange, routing_key, payload):
    exchange = Exchange(exchange, type="topic")
    publisher = PoolPublisher()
    publisher.publish(payload=payload, exchange=exchange, routing_key=routing_key)
    eventlet.sleep(0.5)


if __name__ == "__main__":
    config.parse_args(args={})
    parser = argparse.ArgumentParser(description="Queue producer")
    parser.add_argument(
        "--exchange", required=True, help="Exchange to publish the message to"
    )
    parser.add_argument("--routing-key", required=True, help="Routing key to use")
    parser.add_argument("--payload", required=True, help="Message payload")
    args = parser.parse_args()

    main(exchange=args.exchange, routing_key=args.routing_key, payload=args.payload)
