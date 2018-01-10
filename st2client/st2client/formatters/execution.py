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

import ast
import logging
import struct

import yaml

from st2client import formatters
from st2client.utils import jsutil
from st2client.utils import strutil
from st2client.utils.color import DisplayColors
import six


LOG = logging.getLogger(__name__)

PLATFORM_MAXINT = 2 ** (struct.Struct('i').size * 8 - 1) - 1


class ExecutionResult(formatters.Formatter):

    @classmethod
    def format(cls, entry, *args, **kwargs):
        attrs = kwargs.get('attributes', [])
        attribute_transform_functions = kwargs.get('attribute_transform_functions', {})
        key = kwargs.get('key', None)
        if key:
            output = jsutil.get_value(entry.result, key)
        else:
            # drop entry to the dict so that jsutil can operate
            entry = vars(entry)
            output = ''
            for attr in attrs:
                value = jsutil.get_value(entry, attr)
                value = strutil.strip_carriage_returns(strutil.unescape(value))
                if (isinstance(value, six.string_types) and len(value) > 0 and
                        value[0] in ['{', '['] and value[len(value) - 1] in ['}', ']']):
                    new_value = ast.literal_eval(value)
                    if type(new_value) in [dict, list]:
                        value = new_value
                if type(value) in [dict, list]:
                    # 1. To get a nice overhang indent get safe_dump to generate output with
                    #    the attribute key and then remove the attribute key from the string.
                    # 2. Drop the trailing newline
                    # 3. Set width to maxint so pyyaml does not split text. Anything longer
                    #    and likely we will see other issues like storage :P.
                    formatted_value = yaml.safe_dump({attr: value},
                                                     default_flow_style=False,
                                                     width=PLATFORM_MAXINT,
                                                     indent=2)[len(attr) + 2:-1]
                    value = ('\n' if isinstance(value, dict) else '') + formatted_value
                    value = strutil.dedupe_newlines(value)

                # transform the value of our attribute so things like 'status'
                # and 'timestamp' are formatted nicely
                transform_function = attribute_transform_functions.get(attr,
                                                                       lambda value: value)
                value = transform_function(value=value)

                output += ('\n' if output else '') + '%s: %s' % \
                    (DisplayColors.colorize(attr, DisplayColors.BLUE), value)

        if six.PY3:
            return strutil.unescape(str(output))
        else:
            # Assume Python 2
            return strutil.unescape(str(output)).decode('unicode_escape').encode('utf-8')
