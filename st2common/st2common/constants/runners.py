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

from oslo.config import cfg

__all__ = [
    'LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT',

    'FABRIC_RUNNER_DEFAULT_ACTION_TIMEOUT',
    'FABRIC_RUNNER_DEFAULT_REMOTE_DIR',

    'PYTHON_RUNNER_DEFAULT_ACTION_TIMEOUT',

    'WINDOWS_RUNNER_DEFAULT_ACTION_TIMEOUT',

    'COMMON_ACTION_ENV_VARIABLES'
]

# Local runner
LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT = 60

# Remote (fabric runner)
FABRIC_RUNNER_DEFAULT_ACTION_TIMEOUT = 60

try:
    FABRIC_RUNNER_DEFAULT_REMOTE_DIR = cfg.CONF.ssh_runner.remote_dir
except:
    FABRIC_RUNNER_DEFAULT_REMOTE_DIR = '/tmp'

# Python runner
# Default timeout (in seconds) for actions executed by Python runner
PYTHON_RUNNER_DEFAULT_ACTION_TIMEOUT = 10 * 60

# Windows runner
WINDOWS_RUNNER_DEFAULT_ACTION_TIMEOUT = 10 * 60

# Common st2 environment variables which are available to the actions
COMMON_ACTION_ENV_VARIABLES = [
    'ST2_ACTION_API_URL',
    'ST2_ACTION_AUTH_TOKEN'
]
