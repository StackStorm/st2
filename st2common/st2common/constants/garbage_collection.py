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

__all__ = [
    'DEFAULT_COLLECTION_INTERVAL',
    'DEFAULT_SLEEP_DELAY',
    'MINIMUM_TTL_DAYS',
    'MINIMUM_TTL_DAYS_EXECUTION_OUTPUT'
]


# Default garbage collection interval (in seconds)
DEFAULT_COLLECTION_INTERVAL = 600

# How to long to wait / sleep between collection of different object types (in seconds)
DEFAULT_SLEEP_DELAY = 2

# Minimum value for the TTL. If user supplies value lower than this, we will throw.
MINIMUM_TTL_DAYS = 7

# Minimum TTL in days for action execution output objects.
MINIMUM_TTL_DAYS_EXECUTION_OUTPUT = 1
