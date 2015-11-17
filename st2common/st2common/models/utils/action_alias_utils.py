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

__all__ = [
    'ActionAliasFormatParser'
]


class ActionAliasFormatParser(object):

    def __init__(self, alias_format=None, param_stream=None):
        self._format = alias_format or ''
        self._param_stream = param_stream or ''

    def get_extracted_param_value(self):

        result = {}

        # As there's a lot of questions about using regular expressions,
        # I'll try to be thorough when documenting this code.

        # Firstly, we'll match parameters with default values in form of
        # {{ value = parameter }} (and all possible permutations of spaces),
        # compiling them into a list.
        # "test {{ url = http://google.com }} {{ extra = Test }}" will become
        # [ ["url", "http://google.com"], ["extra", "Test"] ]
        params_list = re.findall(r'{{\s*(.+?)\s*(?:=\s*(.+?))?\s*}}',
                                 self._format, re.DOTALL)

        # Now we're transforming our format string into a regular expression,
        # substituting {{ ... }} with regex named groups, so that param_stream
        # matched against this expression yields a dict of all its params.
        reg = re.sub(r'\s+{{\s*(\S+)\s*=.+?}}', r'(?:\s+(?P<\1>.+?))?',
                     self._format)
        reg = re.sub(r'{{\s*(.+?)\s*}}', r'(?P<\1>.+?)', reg)

        # We're augmenting the expression to include an arbitrary number of
        # optional parameters at the end.
        reg = reg + r'(\s+)?(\s?(\S+)\s*=\s*(\S+))*$'

        # Now we're matching param_stream against our format string regex,
        # getting a dict of values. We'll also get default values from
        # params_list if something is not present.
        match = re.match(reg, self._param_stream, re.DOTALL)
        if match:
            values_dict = match.groupdict()
            for param in params_list:
                result[param[0]] = values_dict[param[0]] or param[1]

        return result
