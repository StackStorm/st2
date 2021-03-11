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

__all__ = [
    "VALID_MODES",
    "DEFAULT_MODE",
    "DEFAULT_BACKEND",
    "HEADER_ATTRIBUTE_NAME",
    "QUERY_PARAM_ATTRIBUTE_NAME",
]

VALID_MODES = ["proxy", "standalone"]

HEADER_ATTRIBUTE_NAME = "X-Auth-Token"
QUERY_PARAM_ATTRIBUTE_NAME = "x-auth-token"

HEADER_API_KEY_ATTRIBUTE_NAME = "St2-Api-Key"
QUERY_PARAM_API_KEY_ATTRIBUTE_NAME = "st2-api-key"

DEFAULT_MODE = "standalone"

DEFAULT_BACKEND = "flat_file"
DEFAULT_SSO_BACKEND = "noop"
