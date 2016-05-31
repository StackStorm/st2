# -*- coding: utf-8 -*-
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

import six

__all__ = [
    'to_unicode'
]


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
