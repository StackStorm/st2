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

__all__ = ["get_config", "set_config"]

# Stores parsed config dictionary
CONFIG = {}


def get_config():
    """
    Retrieve parsed config object.

    :rtype: ``dict``
    """
    global CONFIG
    return CONFIG


def set_config(config):
    """
    Store parsing config object.

    :type config: ``dict``

    :rtype: ``dict``
    """
    global CONFIG
    CONFIG = config
    return config
