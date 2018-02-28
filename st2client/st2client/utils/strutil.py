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
import six


def unescape(s):
    """
    Action execution escapes escaped chars in result (i.e. \n is stored as \\n).
    This function unescapes those chars.
    """
    if isinstance(s, six.string_types):
        s = s.replace('\\n', '\n')
        s = s.replace('\\r', '\r')
        s = s.replace('\\"', '\"')

    return s


def dedupe_newlines(s):
    """yaml.safe_dump converts single newlines to double.

    Since we're printing this output and not loading it, we should
    deduplicate them.
    """

    if isinstance(s, six.string_types):
        s = s.replace('\n\n', '\n')

    return s


def strip_carriage_returns(s):
    if isinstance(s, six.string_types):
        s = s.replace('\\r', '')
        s = s.replace('\r', '')

    return s
