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

from __future__ import absolute_import
import os

__all__ = [
    'DisplayColors',

    'format_status'
]


TERMINAL_SUPPORTS_ANSI_CODES = [
    'xterm',
    'xterm-color',
    'screen',
    'vt100',
    'vt100-color',
    'xterm-256color'
]

DISABLED = os.environ.get('ST2_COLORIZE', '')


class DisplayColors(object):
    RED = '\033[91m'
    PURPLE = '\033[35m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BROWN = '\033[33m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def colorize(value, color=''):
        # TODO: use list of supported terminals
        term = os.environ.get('TERM', None)

        if term is None or term.lower() not in TERMINAL_SUPPORTS_ANSI_CODES:
            # Terminal doesn't support colors
            return value

        if DISABLED or not color:
            return value

        return '%s%s%s' % (color, value, DisplayColors.ENDC)


# Lookup table
STATUS_LOOKUP = {
    'succeeded': DisplayColors.GREEN,
    'delayed': DisplayColors.BLUE,
    'failed': DisplayColors.RED,
    'timeout': DisplayColors.BROWN,
    'running': DisplayColors.YELLOW
}


def format_status(value):
    # Support status values with elapsed info
    split = value.split('(', 1)

    if len(split) == 2:
        status = split[0].strip()
        remainder = '(' + split[1]
    else:
        status = value
        remainder = ''

    color = STATUS_LOOKUP.get(status, DisplayColors.YELLOW)
    result = DisplayColors.colorize(status, color)

    if remainder:
        result = result + ' ' + remainder
    return result
