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
    'prefix_dict_keys'
]


def prefix_dict_keys(dictionary, prefix='_'):
    """
    Prefix dictionary keys with a provided prefix.

    :param dictionary: Dictionary whose keys to prefix.
    :type dictionary: ``dict``

    :param prefix: Key prefix.
    :type prefix: ``str``

    :rtype: ``dict``:
    """
    result = {}

    for key, value in six.iteritems(dictionary):
        result['%s%s' % (prefix, key)] = value

    return result


def strip_last_newline_char(input_str):
    """
    Strips the last char if its newline.

    :param input_str: Input string to be stripped.
    :type input_str: ``str``

    :rtype: ``str``
    """
    if not input_str:
        return input_str

    if input_str.endswith('\n'):
        return input_str[:-1]

    return input_str
