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

try:
    import simplejson as json
except ImportError:
    import json

import six
from pecan.jsonify import GenericJSON


__all__ = [
    'json_encode',
    'json_loads',
    'try_loads'
]


def json_encode(obj, indent=4):
    return json.dumps(obj, cls=GenericJSON, indent=indent)


def load_file(path):
    with open(path, 'r') as fd:
        return json.load(fd)


def json_loads(obj, keys=None):
    """
    Given an object, this method tries to json.loads() the value of each of the keys. If json.loads
    fails, the original value stays in the object.

    :param obj: Original object whose values should be converted to json.
    :type obj: ``dict``

    :param keys: Optional List of keys whose values should be transformed.
    :type keys: ``list``

    :rtype ``dict`` or ``None``
    """
    if not obj:
        return None

    if not keys:
        keys = obj.keys()

    for key in keys:
        try:
            obj[key] = json.loads(obj[key])
        except:
            pass
    return obj


def try_loads(s):
    try:
        return json.loads(s) if s and isinstance(s, six.string_types) else s
    except:
        return s
