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

from __future__ import absolute_import

import os

from st2common import __version__

__all__ = [
    "VERSION_STRING",
    "DEFAULT_CONFIG_FILE_PATH",
    "API_URL_ENV_VARIABLE_NAME",
    "AUTH_TOKEN_ENV_VARIABLE_NAME",
]

VERSION_STRING = "StackStorm v%s" % (__version__)
DEFAULT_CONFIG_FILE_PATH = os.environ.get("ST2_CONFIG_PATH", "/etc/st2/st2.conf")

API_URL_ENV_VARIABLE_NAME = "ST2_API_URL"
AUTH_TOKEN_ENV_VARIABLE_NAME = "ST2_AUTH_TOKEN"
