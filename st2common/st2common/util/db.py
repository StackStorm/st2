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

import mongoengine
import six


def mongodb_to_python_types(value):
    # Convert MongoDB BaseDict and BaseList types to python dict and list types.
    if isinstance(value, mongoengine.base.datastructures.BaseDict):
        value = dict(value)
    elif isinstance(value, mongoengine.base.datastructures.BaseList):
        value = list(value)

    # Recursively traverse the dict and list to convert values.
    if isinstance(value, dict):
        value = {k: mongodb_to_python_types(v) for k, v in six.iteritems(value)}
    elif isinstance(value, list):
        value = [mongodb_to_python_types(v) for v in value]

    return value
