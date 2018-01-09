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

from __future__ import absolute_import
import copy

import six

__all__ = [
    'merge_dicts'
]


def merge_dicts(d1, d2):
    """
    Merge values from d2 into d1 ignoring empty / None values.

    :type d1: ``dict``
    :type d2: ``dict``

    :rtype: ``dict``
    """
    result = copy.deepcopy(d1)

    for key, value in six.iteritems(d2):
        if isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        elif key not in result or value is not None:
            result[key] = value

    return result
