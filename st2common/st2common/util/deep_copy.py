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

__all__ = ["fast_deepcopy_dict"]


def default(obj):
    # NOTE: For some reason isinstance check doesn't work here so we use class name check
    if obj.__class__.__name__ == "ObjectId":
        return str(obj)
    raise TypeError


def fast_deepcopy_dict(value, fall_back_to_deepcopy=True):
    """
    Perform a fast deep copy of the provided value.

    This function is designed primary to operate on values of a simple type (think JSON types -
    dicts, lists, arrays, strings, ints).

    It's up to 10x faster compared to copy.deepcopy().

    In case the provided value contains non-simple types, we simply fall back to "copy.deepcopy()".
    This means that we can still use it on values which sometimes, but not always contain complex
    types - in that case, when value doesn't contain complex types we will perform much faster copy
    and when it does, we will simply fall back to copy.deepcopy().

    :param fall_back_to_deepcopy: True to fall back to copy.deepcopy() in case we fail to fast deep
                                  copy the value because it contains complex types or similar
    :type fall_back_to_deepcopy: ``bool``
    """
    # NOTE: ujson / orjson round-trip is up to 10 times faster on smaller and larger dicts compared
    # to copy.deepcopy(), but it has some edge cases with non-simple types such as datetimes, class
    # instances, etc.
    try:
        value = orjson.loads(orjson.dumps(value, default=default))
    except (OverflowError, ValueError, TypeError) as e:
        if not fall_back_to_deepcopy:
            raise e

        value = copy.deepcopy(value)

    return value
