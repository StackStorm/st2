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
import argparse

try:
    import pika  # pylint disable=import-error
except ImportError:
    raise ImportError(
        "Pika is not installed with StackStorm. Install it manually to use this tool."
    )


def main(queue, payload):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host="localhost",
            credentials=pika.credentials.PlainCredentials(
                username="guest", password="guest"
            ),
        )
    )
    channel = connection.channel()

    channel.queue_declare(queue=queue, durable=True)

    channel.basic_publish(exchange="", routing_key=queue, body=payload)
    print("Sent %s" % payload)
    connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Direct queue publisher")
    parser.add_argument("--queue", required=True, help="Routing key to use")
    parser.add_argument("--payload", required=True, help="Message payload")
    args = parser.parse_args()

    main(queue=args.queue, payload=args.payload)
