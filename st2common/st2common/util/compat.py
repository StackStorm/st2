# -*- coding: utf-8 -*-
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

"""
Module with Python 3 related compatibility functions.
"""

from __future__ import absolute_import

import six


__all__ = [
    "mock_open_name",
    "to_unicode",
    "to_ascii",
]

if six.PY3:
    mock_open_name = "builtins.open"
else:
    mock_open_name = "__builtin__.open"


def to_unicode(value):
    """
    Ensure that the provided text value is represented as unicode.

    :param value: Value to convert.
    :type value: ``str`` or ``unicode``

    :rtype: ``unicode``
    """
    if not isinstance(value, six.string_types):
        raise ValueError('Value "%s" must be a string.' % (value))

    if not isinstance(value, six.text_type):
        value = six.u(value)

    return value


def to_ascii(value):
    """
    Function which encodes the provided bytes / string to ASCII encoding ignoring any errors
    which could come up when trying to encode a non-ascii value.
    """

    if six.PY3:
        value = value.encode()

    return value.decode("ascii", errors="ignore")
