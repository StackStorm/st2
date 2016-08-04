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

import re
import six

__all__ = [
    'regex_match',
    'regex_replace',
    'regex_search'
]


def _get_regex_flags(ignorecase=False):
    return re.I if ignorecase else 0


def regex_match(value, pattern='', ignorecase=False):
    if not isinstance(value, six.string_types):
        value = str(value)
    flags = _get_regex_flags(ignorecase)
    return bool(re.match(pattern, value, flags))


def regex_replace(value='', pattern='', replacement='', ignorecase=False):
    if not isinstance(value, six.string_types):
        value = str(value)
    flags = _get_regex_flags(ignorecase)
    regex = re.compile(pattern, flags)
    return regex.sub(replacement, value)


def regex_search(value, pattern='', ignorecase=False):
    if not isinstance(value, six.string_types):
        value = str(value)
    flags = _get_regex_flags(ignorecase)
    return bool(re.search(pattern, value, flags))
