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

import logging

__all__ = [
    'ExclusionFilter',
    'LogLevelFilter',
]


class ExclusionFilter(object):

    def __init__(self, exclusions):
        self._exclusions = set(exclusions)

    def filter(self, record):
        if len(self._exclusions) < 1:
            return True
        module_decomposition = record.name.split('.')
        exclude = len(module_decomposition) > 0 and module_decomposition[0] in self._exclusions
        return not exclude


class LogLevelFilter(logging.Filter):
    """
    Filter which excludes log messages which match the provided log levels.
    """

    def __init__(self, log_levels):
        self._log_levels = log_levels

    def filter(self, record):
        level = record.levelno
        if level in self._log_levels:
            return False

        return True
