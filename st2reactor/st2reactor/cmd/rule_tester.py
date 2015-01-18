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

import argparse
import logging as std_logging
import os
import pprint
import sys

from st2common import log as logging
from st2reactor.rules.tester import RuleTester

__all__ = [
    'main'
]


def _parse_args():
    parser = argparse.ArgumentParser(description='Test the provided rule')
    parser.add_argument('--rule', help='Path to the file containing rule definition',
                        required=True)
    parser.add_argument('--trigger-instance',
                        help='Path to the file containing trigger instance definition',
                        required=True)
    parser.add_argument('-v', '--verbose', help='increase output verbosity',
                        action='store_true')
    return parser.parse_args()


def _setup_logging():
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '%(asctime)s %(levelname)s %(name)s %(message)s'
            },
        },
        'handlers': {
            'console': {
                '()': std_logging.StreamHandler,
                'formatter': 'default'
            }
        },
        'root': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
    std_logging.config.dictConfig(logging_config)


def main():
    args = _parse_args()
    if args.verbose:
        _setup_logging()
        output = logging.getLogger(__name__).info
    else:
        output = pprint.pprint

    rule_file_path = os.path.realpath(args.rule)
    trigger_instance_file_path = os.path.realpath(args.trigger_instance)

    tester = RuleTester(rule_file_path=rule_file_path,
                        trigger_instance_file_path=trigger_instance_file_path)
    matches = tester.evaluate()

    if matches:
        output('=== RULE MATCHES ===')
        sys.exit(0)
    else:
        output('=== RULE DOES NOT MATCH ===')
        sys.exit(1)
