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
This module contains handler methods for different signals which are handled in the same way across
the whole code base.
"""

from __future__ import absolute_import

import signal
import logging

from st2common.logging.misc import reopen_log_files

__all__ = [
    "register_common_signal_handlers",
]


def register_common_signal_handlers():
    signal.signal(signal.SIGUSR1, handle_sigusr1)


def handle_sigusr1(signal_number, stack_frame):
    """
    Global SIGUSR1 signal handler which causes all the loggers to re-open log file handles.

    Note: This function is used with log rotation utilities such as logrotate.
    """
    handlers = logging.getLoggerClass().manager.root.handlers
    reopen_log_files(handlers=handlers)
