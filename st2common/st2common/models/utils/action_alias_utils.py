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

        # I'll split the whole convoluted regex into snippets to make it
        # a bit more readable (hopefully).
        snippets = dict()

        # Formats for keys and values: key is a non-spaced string,
        # value is anything in quotes or curly braces, or a single word.
        snippets['key'] = r'\s*(\S+?)\s*'
        snippets['value'] = r'""|\'\'|"(.+?)"|\'(.+?)\'|({.+?})|(\S+)'

        # Extended value: also matches unquoted text (caution).
        snippets['ext_value'] = r'""|\'\'|"(.+?)"|\'(.+?)\'|({.+?})|(.+?)'

        # Key-value pair:
        snippets['pairs'] = r'(?:^|\s+){key}=({value})'.format(**snippets)

        # End of string: multiple space-separated key-value pairs:
        snippets['ending'] = r'.*?(({pairs}\s*)*)$'.format(**snippets)

        # Default value in optional parameters:
        snippets['default'] = r'\s*=\s*(?:{ext_value})\s*'.format(**snippets)

        # Optional parameter (has a default value):
        snippets['optional'] = '{{' + snippets['key'] + snippets['default'] + '}}'

        # Required parameter (no default value):
        snippets['required'] = '{{' + snippets['key'] + '}}'

        # 1. Matching the arbitrary key-value pairs at the end of the command
        # to support extra parameters (not specified in the format string),
        # and cutting them from the command string afterwards.
        ending_pairs = re.match(snippets['ending'], self._param_stream, re.DOTALL)
        if ending_pairs:
            kv_pairs = re.findall(snippets['pairs'], ending_pairs.group(1), re.DOTALL)
            self._param_stream = self._param_stream.replace(ending_pairs.group(1), '')
        self._param_stream = " %s " % self._param_stream

        # 2. Matching optional parameters (with default values).
        optional = re.findall(snippets['optional'], self._format, re.DOTALL)

        # Transforming our format string into a regular expression,
        # substituting {{ ... }} with regex named groups, so that param_stream
        # matched against this expression yields a dict of params with values.
        param_match = r'\1["\']?(?P<\2>(?:(?<=\').+?(?=\')|(?<=").+?(?=")|{.+?}|.+?))["\']?'
        reg = re.sub(r'(\s*)' + snippets['optional'], r'(?:' + param_match + r')?', self._format)
        reg = re.sub(r'(\s*)' + snippets['required'], param_match, reg)
        reg = '^\s*' + reg + r'\s*$'

        # 3. Matching the command against our regex to get the param values
        matched_stream = re.match(reg, self._param_stream, re.DOTALL)

        # Compiling results from the steps 1-3.
        if matched_stream:
            result = matched_stream.groupdict()
        for param in optional:
            matched_value = result[param[0]] if matched_stream else None
            matched_result = matched_value or ''.join(param[1:])
            if matched_result is not None:
                result[param[0]] = matched_result
        if ending_pairs:
            for pair in kv_pairs:
                result[pair[0]] = ''.join(pair[2:])

        if self._format and not (self._param_stream.strip() or any(result.values())):
            raise content.ParseException('No value supplied and no default value found.')

        return result
