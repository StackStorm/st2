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

import copy

import orjson

__all__ = [
    'fast_deepcopy'
]


def default(obj):
    # NOTE: For some reason isinstance check doesn't work here so we use class name check
    if obj.__class__.__name__ == "ObjectId":
        return str(obj)
    raise TypeError


def fast_deepcopy(value, fall_back_to_deepcopy=True):
    """
    Perform a fast deepcopy of the provided value.

    :param fall_back_to_deepcopy: True to fall back to copy.deepcopy() in case ujson throws an
                                  exception.
    :type fall_back_to_deepcopy: ``bool``
    """
    # NOTE: ujson / ujson round-trip is up to 10 times faster on smaller and larger dicts compared
    # to copy.deepcopy(), but it has some edge cases with non-simple types such as datetimes
    try:
        # NOTE: ujson serialized datetime to seconds since epoch (int) whereas orjson serializes it
        # to a  RFC 3339 string by default
        value = orjson.loads(orjson.dumps(value, default=default))
    except (OverflowError, ValueError) as e:
        # NOTE: ujson doesn't support 5 or 6 bytes utf-8 sequences which we use
        # in our tests so we fall back to deep copy
        if not fall_back_to_deepcopy:
            raise e

        value = copy.deepcopy(value)

    return value
