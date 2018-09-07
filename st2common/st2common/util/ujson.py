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

import ujson

__all__ = [
    'fast_deepcopy'
]


def fast_deepcopy(value, fall_back_to_deepcopy=False):
    """
    Perform a fast deepcopy of the provided value.

    :param fall_back_to_deepcopy: True to fall back to copy.deepcopy() in case ujson throws an
                                  exception.
    :type fall_back_to_deepcopy: ``bool``
    """
    # NOTE: We perform a lazy import to avoid issues with Python 3 virtualenvs on Python 2
    # deployments

    # NOTE: ujson round-trip is up to 10 times faster on smaller and larger dicts compared
    # to copy.deepcopy(), but it has some edge cases with non-simple types such as datetimes -
    try:
        value = ujson.loads(ujson.dumps(value))
    except (OverflowError, ValueError) as e:
        # NOTE: ujson doesn't support 5 or 6 bytes utf-8 sequences which we use
        # in our tests so we fall back to deep copy
        if not fall_back_to_deepcopy:
            raise e

        value = copy.deepcopy(value)

    return value
