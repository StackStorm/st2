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
from st2common.exceptions import content

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

        # We're parsing the arbitrary key-value pairs at the end of the stream
        # to support passing of parameters not specified in the format string,
        # and cutting them from the stream as they're no longer needed.
        # Possible values are quoted strings, a word, or anything inside "{}".
        pairs_match = r'(?:^|\s+)(\S+)=("(.*?)"|\'(.*?)\'|({.*?})|(\S+))'
        extra = re.match(r'.*?((' + pairs_match + r'\s*)*)$',
                         self._param_stream, re.DOTALL)
        if extra:
            kv_pairs = re.findall(pairs_match,
                                  extra.group(1), re.DOTALL)
            for pair in kv_pairs:
                result[pair[0]] = ''.join(pair[2:])
            self._param_stream = self._param_stream.replace(extra.group(1), '')
        self._param_stream = " %s " % self._param_stream

        # Now we'll match parameters with default values in form of
        # {{ value = parameter }} (and all possible permutations of spaces),
        # compiling them into a list.
        # "test {{ url = http://google.com }} {{ extra = Test }}" will become
        # [ ["url", "http://google.com"], ["extra", "Test"] ]
        params = re.findall(r'{{\s*(.+?)\s*(?:=\s*[\'"]?({.+?}|.+?)[\'"]?)?\s*}}',
                            self._format, re.DOTALL)

        # Now we're transforming our format string into a regular expression,
        # substituting {{ ... }} with regex named groups, so that param_stream
        # matched against this expression yields a dict of params with values.
        param_match = r'["\']?(?P<\2>(?:(?<=\').+?(?=\')|(?<=").+?(?=")|{.+?}|.+?))["\']?'
        reg = re.sub(r'(\s*){{\s*([^=]+?)\s*}}(?=\s+{{[^}]+?=)',
                     r'\s*' + param_match + r'\s+',
                     self._format)
        reg = re.sub(r'(\s*){{\s*(\S+)\s*=\s*(?:{.+?}|.+?)\s*}}(\s*)',
                     r'(?:\s*' + param_match + r'\s+)?\s*',
                     reg)
        reg = re.sub(r'(\s*){{\s*(.+?)\s*}}(\s*)',
                     r'\s*' + param_match + r'\3',
                     reg)
        reg = '^\s*' + reg + r'\s*$'

        # Now we're matching param_stream against our format string regex,
        # getting a dict of values. We'll also get default values from
        # "params" list if something is not present.
        matched_stream = re.match(reg, self._param_stream, re.DOTALL)
        if matched_stream:
            print matched_stream.groupdict()
            values = matched_stream.groupdict()
        for param in params:
            matched_value = values[param[0]] if matched_stream else None
            result[param[0]] = matched_value or param[1]

        if self._format and not (self._param_stream.strip() or any(result.values())):
            raise content.ParseException('No value supplied and no default value found.')

        return result
