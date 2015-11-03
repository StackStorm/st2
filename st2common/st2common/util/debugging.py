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
Module containing various debugging functionality.
"""

__all__ = [
    'enable_debugging',
    'disable_debugging',
    'is_enabled'
]

ENABLE_DEBUGGING = False


def enable_debugging():
    global ENABLE_DEBUGGING
    ENABLE_DEBUGGING = True
    return ENABLE_DEBUGGING


def disable_debugging():
    global ENABLE_DEBUGGING
    ENABLE_DEBUGGING = False
    return ENABLE_DEBUGGING


def is_enabled():
    global ENABLE_DEBUGGING
    return ENABLE_DEBUGGING
