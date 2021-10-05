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

__all__ = ["get_url_without_trailing_slash"]


def get_url_without_trailing_slash(value):
    """
    Function which strips a trailing slash from the provided url if one is present.

    :param value: URL to format.
    :type value: ``str``

    :rtype: ``str``
    """
    result = value[:-1] if value.endswith("/") else value
    return result
