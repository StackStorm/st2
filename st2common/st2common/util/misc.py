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

import logging

import os
import re
import sys
import functools

import six
from collections.abc import Mapping

__all__ = [
    "prefix_dict_keys",
    "compare_path_file_name",
    "get_field_name_from_mongoengine_error",
    "sanitize_output",
    "strip_shell_chars",
    "rstrip_last_char",
    "lowercase_value",
]


def prefix_dict_keys(dictionary, prefix="_"):
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
        result["%s%s" % (prefix, key)] = value

    return result


def compare_path_file_name(file_path_a, file_path_b):
    """
    Custom compare function which compares full absolute file paths just using
    the file name.

    This function can be used with ``sorted`` or ``list.sort`` function.
    """
    file_name_a = os.path.basename(file_path_a)
    file_name_b = os.path.basename(file_path_b)

    return (file_name_a > file_name_b) - (file_name_a < file_name_b)


def sanitize_output(input_str, uses_pty=False):
    """
    Function which sanitizes paramiko output (stdout / stderr).

    It strips trailing carriage return and new line characters and if pty is used, it also replaces
    all occurrences of \r\n with \n.

    By default when pty is used, all \n characters are convered to \r\n and that's not desired
    in our remote runner action output.

    :param input_str: Input string to be sanitized.
    :type input_str: ``str``

    :rtype: ``str``

    """
    output = strip_shell_chars(input_str)

    if uses_pty:
        output = output.replace("\r\n", "\n")

    return output


def strip_shell_chars(input_str):
    """
    Strips the last '\r' or '\n' or '\r\n' string at the end of
    the input string. This is typically used to strip ``stdout``
    and ``stderr`` streams of those characters.

    :param input_str: Input string to be stripped.
    :type input_str: ``str``

    :rtype: ``str``
    """
    stripped_str = rstrip_last_char(input_str, "\n")
    stripped_str = rstrip_last_char(stripped_str, "\r")
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
        return input_str[: -len(char_to_strip)]

    return input_str


def deep_update(d, u):
    """
    Perform deep merge / update of the target dict.
    """

    for k, v in six.iteritems(u):
        if isinstance(v, Mapping):
            r = deep_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]

    return d


def get_normalized_file_path(file_path):
    """
    Return a full normalized file path for the provided path string.

    :rtype: ``str``
    """
    if hasattr(sys, "frozen"):  # support for py2exe
        file_path = "logging%s__init__%s" % (os.sep, file_path[-4:])
    elif file_path[-4:].lower() in [".pyc", ".pyo"]:
        file_path = file_path[:-4] + ".py"
    else:
        file_path = file_path

    file_path = os.path.normcase(file_path)
    return file_path


def lowercase_value(value):
    """
    Lowercase the provided value.

    In case of a list, all the string item values are lowercases and in case of a dictionary, all
    of the string keys and values are lowercased.
    """
    if isinstance(value, six.string_types):
        result = value.lower()
    elif isinstance(value, (list, tuple)):
        result = [str(item).lower() for item in value]
    elif isinstance(value, dict):
        result = {}
        for key, value in six.iteritems(value):
            result[key.lower()] = str(value).lower()
    else:
        result = value

    return result


def get_field_name_from_mongoengine_error(exc):
    """
    Try to extract field name from mongoengine error.

    If field name is unable to be extracted, original exception is returned instead.
    """
    msg = str(exc)

    match = re.match('Cannot resolve field "(.+?)"', msg)

    if match:
        return match.groups()[0]

    return msg


def ignore_and_log_exception(
    exc_classes=(Exception,), logger=None, level=logging.WARNING
):
    """
    Decorator which catches the provided exception classes and logs them instead of letting them
    bubble all the way up.
    """
    exc_classes = tuple(exc_classes)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exc_classes as e:
                if len(args) >= 1 and getattr(args[0], "__class__", None):
                    func_name = "%s.%s" % (args[0].__class__.__name__, func.__name__)
                else:
                    func_name = func.__name__

                message = 'Exception in fuction "%s": %s' % (func_name, str(e))
                logger.log(level, message)

        return wrapper

    return decorator
