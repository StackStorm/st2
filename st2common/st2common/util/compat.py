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

import sys

import six


__all__ = [
    'to_unicode',
    'to_ascii',
    'add_st2actions_pythonrunner_to_sys_path'
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


def to_ascii(value):
    """
    Function which encodes the provided bytes / string to ASCII encoding ignoring any errors
    which could come up when trying to encode a non-ascii value.
    """
    return value.decode('ascii', errors='ignore')


def add_st2actions_pythonrunner_to_sys_path():
    """
    Function which adds "st2common.runners.pythonrunner" to sys.path and redirects it to
    "st2common.runners.base_action".

    First path was deprecated a long time ago, but some modules still rely on on it. This
    is to be used in places where "st2common" is used as a standalone package without access to
    st2actions (e.g. serverless).
    """
    import st2common.runners.base_action

    sys.modules['st2actions'] = {}
    sys.modules['st2actions.runners'] = {}
    sys.modules['st2actions.runners.pythonrunner'] = st2common.runners.base_action

    return sys.modules
