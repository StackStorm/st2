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

import ast
import json

from st2common.util.compat import to_unicode


def _cast_object(x):
    if isinstance(x, str) or isinstance(x, unicode):
        try:
            return json.loads(x)
        except:
            return ast.literal_eval(x)
    else:
        return x


# These types as they appear in json schema.
CASTS = {
    'array': (lambda x: ast.literal_eval(x) if isinstance(x, str) or isinstance(x, unicode)
              else x),
    'boolean': (lambda x: ast.literal_eval(x.capitalize())
                if isinstance(x, str) or isinstance(x, unicode) else x),
    'integer': int,
    'number': float,
    'object': _cast_object,
    'string': to_unicode
}


def get_cast(cast_type):
    """
    Determines the callable which will perform the cast given a string representation
    of the type.

    :param cast_type: Type of the cast to perform.
    :type cast_type: ``str``

    :rtype: ``callable``
    """
    return CASTS.get(cast_type, None)
