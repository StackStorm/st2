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

import json

__all__ = [
    'json_escape'
]


def json_escape(value):
    """ Adds escape sequences to problematic characters in the string

    This filter simply passes the value to json.dumps
    as a convenient way of escaping characters in it

    However, before returning, we want to strip the double
    quotes at the ends of the string, since we're not looking
    for a valid JSON value at the end, just conveniently using
    this function to do the escaping. The value could be any
    arbitrary value
    """

    return json.dumps(value).strip('"')
