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

# Minimum poll interval for a sensor
MINIMUM_POLL_INTERVAL = 4

# keys for PARTITION loaders
DEFAULT_PARTITION_LOADER = "default"
KVSTORE_PARTITION_LOADER = "kvstore"
FILE_PARTITION_LOADER = "file"
HASH_PARTITION_LOADER = "hash"

# Sensor respawn / retry defaults (overridable via the [sensorcontainer] config
# group: max_respawn_count, respawn_delay, respawn_backoff_factor).
#
# How many times to subsequently respawn a sensor after a non-zero exit before
# giving up (and firing the process_abandoned trigger).
DEFAULT_SENSOR_MAX_RESPAWN_COUNT = 2
# Base delay (in seconds) to wait between respawn attempts.
DEFAULT_SENSOR_RESPAWN_DELAY = 2.5
# Exponential backoff multiplier applied to the base delay per attempt. A value
# of 1 (the default) means a constant delay between attempts; a value > 1 grows
# the delay exponentially (delay * factor ** (attempt - 1)).
DEFAULT_SENSOR_RESPAWN_BACKOFF_FACTOR = 1.0

# Runtime status values recorded for a running sensor instance (SensorInstanceDB)
SENSOR_STATUS_RUNNING = "running"
SENSOR_STATUS_STOPPED = "stopped"
SENSOR_STATUS_ABANDONED = "abandoned"

SENSOR_STATUSES = [
    SENSOR_STATUS_RUNNING,
    SENSOR_STATUS_STOPPED,
    SENSOR_STATUS_ABANDONED,
]
