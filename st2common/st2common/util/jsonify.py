# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from st2common import log as logging

LOG = logging.getLogger(__name__)

try:
    import simplejson as json
    from simplejson import JSONEncoder
except ImportError:
    import json
    from json import JSONEncoder

import six
import bson
import orjson


__all__ = [
    "json_encode",
    "json_decode",
    "json_loads",
    "try_loads",
    "get_json_type_for_python_value",
]

# Which json library to use for data serialization and deserialization.
# We only expose this option so we can exercise code paths with different libraries inside the
# tests for compatibility reasons
DEFAULT_JSON_LIBRARY = "orjson"


class GenericJSON(JSONEncoder):
    def default(self, obj):  # pylint: disable=method-hidden
        if hasattr(obj, "__json__") and six.callable(obj.__json__):
            return obj.__json__()
        elif isinstance(obj, bson.ObjectId):
            return str(obj)
        else:
            return JSONEncoder.default(self, obj)


def default(obj):
    if hasattr(obj, "__json__") and six.callable(obj.__json__):
        return obj.__json__()
    elif isinstance(obj, bytes):
        # TODO: We should update the code which passes bytes to pass unicode to avoid this
        # conversion here
        return obj.decode("utf-8")
    elif isinstance(obj, bson.ObjectId):
        return str(obj)
    raise TypeError


def json_encode_native_json(obj, indent=4, sort_keys=False):
    if not indent:
        separators = (",", ":")
    else:
        separators = None
    return json.dumps(
        obj, cls=GenericJSON, indent=indent, separators=separators, sort_keys=sort_keys
    )


def json_encode_orjson(obj, indent=None, sort_keys=False):
    option = None

    if indent:
        # NOTE: We don't use indent by default since it's quite a bit slower
        option = orjson.OPT_INDENT_2

    if sort_keys:
        option = option | orjson.OPT_SORT_KEYS if option else orjson.OPT_SORT_KEYS

    if option:
        return orjson.dumps(obj, default=default, option=option).decode("utf-8")

    return orjson.dumps(obj, default=default).decode("utf-8")


def json_decode_native_json(data):
    return json.loads(data)


def json_decode_orjson(data):
    return orjson.loads(data)


def json_encode(obj, indent=None, sort_keys=False):
    """
    Wrapper function for encoding the provided object.

    This function automatically select appropriate JSON library based on the configuration value.

    This function should be used everywhere in the code base where json.dumps() behavior is desired.
    """
    json_library = DEFAULT_JSON_LIBRARY

    if json_library == "json":
        return json_encode_native_json(obj=obj, indent=indent, sort_keys=sort_keys)
    elif json_library == "orjson":
        return json_encode_orjson(obj=obj, indent=indent, sort_keys=sort_keys)
    else:
        raise ValueError("Unsupported json_library: %s" % (json_library))


def json_decode(data):
    """
    Wrapper function for decoding the provided JSON string.

    This function automatically select appropriate JSON library based on the configuration value.

    This function should be used everywhere in the code base where json.loads() behavior is desired.
    """
    json_library = DEFAULT_JSON_LIBRARY

    if json_library == "json":
        return json_decode_native_json(data=data)
    elif json_library == "orjson":
        return json_decode_orjson(data=data)
    else:
        raise ValueError("Unsupported json_library: %s" % (json_library))


def load_file(path):
    with open(path, "r") as fd:
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
        keys = list(obj.keys())

    for key in keys:
        try:
            obj[key] = json_decode(obj[key])
        except Exception:
            # NOTE: This exception is not fatal so we intentionally don't log anything.
            # Method behaves in "best effort" manner and dictionary value not being JSON
            # string is perfectly valid (and common) scenario so we should not log anything
            pass
    return obj


def try_loads(s):
    try:
        return json_decode(s) if s and isinstance(s, six.string_types) else s
    except:
        return s


def get_json_type_for_python_value(value):
    """
    Return JSON type string for the provided Python value.

    :rtype: ``str``
    """
    if isinstance(value, six.text_type):
        return "string"
    elif isinstance(value, (int, float)):
        return "number"
    elif isinstance(value, dict):
        return "object"
    elif isinstance(value, (list, tuple)):
        return "array"
    elif isinstance(value, bool):
        return "boolean"
    elif value is None:
        return "null"
    else:
        return "unknown"
