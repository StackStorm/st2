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

import os

import six

__all__ = [
    'prefix_dict_keys',
    'compare_path_file_name'
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


def compare_path_file_name(file_path_a, file_path_b):
    """
    Custom compare function which compares full absolute file paths just using
    the file name.

    This function can be used with ``sorted`` or ``list.sort`` function.
    """
    file_name_a = os.path.basename(file_path_a)
    file_name_b = os.path.basename(file_path_b)

    return file_name_a < file_name_b


def strip_shell_chars(input_str):
    """
    Strips the last '\r' or '\n' or '\r\n' string at the end of
    the input string. This is typically used to strip ``stdout``
    and ``stderr`` streams of those characters.

    :param input_str: Input string to be stripped.
    :type input_str: ``str``

    :rtype: ``str``
    """
    stripped_str = rstrip_last_char(input_str, '\n')
    stripped_str = rstrip_last_char(stripped_str, '\r')
    return stripped_str


def rstrip_last_char(input_str, char_to_strip):
    """
    Strips the last `char_to_strip` from input_str if
    input_str ends with `char_to_strip`.

    :param input_str: Input string to be stripped.
    :type input_str: ``str``

    :rtype: ``str``
    """
    if not input_str:
        return input_str

    if not char_to_strip:
        return input_str

    if input_str.endswith(char_to_strip):
        return input_str[:-len(char_to_strip)]

    return input_str
