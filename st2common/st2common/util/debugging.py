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
Module containing various debugging functionality.
"""

from __future__ import absolute_import
import paramiko
from kombu.utils.debug import setup_logging

import logging as stdlib_logging

from st2common.logging.misc import set_log_level_for_all_loggers

__all__ = ["enable_debugging", "disable_debugging", "is_enabled"]

ENABLE_DEBUGGING = False


def enable_debugging():
    global ENABLE_DEBUGGING
    ENABLE_DEBUGGING = True

    # Set debug level for all StackStorm loggers
    set_log_level_for_all_loggers(level=stdlib_logging.DEBUG)

    # Set debug log level for kombu
    setup_logging(loglevel=stdlib_logging.DEBUG)

    # Set debug log level for paramiko
    paramiko.common.logging.basicConfig(level=paramiko.common.DEBUG)

    return ENABLE_DEBUGGING


def disable_debugging():
    global ENABLE_DEBUGGING
    ENABLE_DEBUGGING = False

    set_log_level_for_all_loggers(level=stdlib_logging.INFO)

    setup_logging(loglevel=stdlib_logging.INFO)
    paramiko.common.logging.basicConfig(level=paramiko.common.INFO)

    return ENABLE_DEBUGGING


def is_enabled():
    global ENABLE_DEBUGGING
    return ENABLE_DEBUGGING
