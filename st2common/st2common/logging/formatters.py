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

import logging
import socket
import time
import json
import copy
import traceback

import six

from st2common.constants.secrets import MASKED_ATTRIBUTES_BLACKLIST
from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE

__all__ = [
    'ConsoleLogFormatter',
    'GelfLogFormatter',
]

SIMPLE_TYPES = (int, float) + six.string_types
NON_OBJECT_TYPES = SIMPLE_TYPES + (list, dict) + six.string_types

# GELF logger specific constants
HOSTNAME = socket.gethostname()
GELF_SPEC_VERSION = '1.1'

COMMON_ATTRIBUTE_NAMES = [
    'process',
    'processName',
    'module',
    'filename',
    'funcName',
    'lineno'
]


def serialize_object(obj):
    """
    Serialize the provided object.

    We look for "to_dict" and "to_serializable_dict" methods. If none of those methods is
    available, we fall back to "repr(obj)".

    :rtype: ``str``
    """
    # Try to serialize the object
    if getattr(obj, 'to_dict', None):
        value = obj.to_dict()
    elif getattr(obj, 'to_serializable_dict', None):
        value = obj.to_serializable_dict(mask_secrets=True)
    else:
        value = repr(obj)

    return value


def process_attribute_value(key, value):
    """
    Format and process the extra attribute value.
    """
    # NOTE: This can be expensive when processing large dicts or objects
    if isinstance(value, SIMPLE_TYPES):
        if key in MASKED_ATTRIBUTES_BLACKLIST:
            value = MASKED_ATTRIBUTE_VALUE
    elif isinstance(value, dict):
        # Note: We don't want to modify the original value
        value = copy.deepcopy(value)

        for dict_key, dict_value in six.iteritems(value):
            value[dict_key] = process_attribute_value(key=dict_key, value=dict_value)

    return value


class ObjectJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder which also knows how to encode objects.
    """

    # pylint: disable=method-hidden
    def default(self, obj):
        if isinstance(obj, object):
            value = serialize_object(obj=obj)
            return value

        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class BaseExtraLogFormatter(logging.Formatter):
    """
    Base class for the log formatters which expect additional context to be passed in the "extra"
    dictionary.

    For example:

    extra={'_id': 'user-1', '_path': '/foo/bar'}

    Note: To avoid clashes with standard Python log record attributes, all the keys in the extra
    dictionary need to be prefixed with a slash ('_').
    """

    PREFIX = '_'  # Prefix for user provided attributes in the extra dict

    def _get_extra_attributes(self, record):
        attributes = dict([(k, v) for k, v in six.iteritems(record.__dict__)
                           if k.startswith(self.PREFIX)])
        return attributes

    def _get_common_extra_attributes(self, record):
        result = {}

        for name in COMMON_ATTRIBUTE_NAMES:
            value = getattr(record, name, None)

            if not value:
                continue

            result[name] = value

        return result

    def _format_extra_attributes(self, attributes):
        result = {}
        for key, value in six.iteritems(attributes):
            if isinstance(value, NON_OBJECT_TYPES):
                # Leave non-object types as is
                value = value
            elif isinstance(value, object):
                # Check for a custom serialization method and serialize the value
                value = serialize_object(obj=value)

            # Note: We remove leading _ from the key
            value = process_attribute_value(key=key[1:], value=value)
            result[key] = value

        return result


class ConsoleLogFormatter(BaseExtraLogFormatter):
    """
    Formatter which attaches all the attributes from the "extra" dictionary as key=value pairs to
    the end of the log message.

    For example:

        LOG.info('Hello world', extra={'_id': 1, '_path': '/fooo'})

    Result:

        Hello World (id=1,path=foo)
    """

    def format(self, record):
        attributes = self._get_extra_attributes(record=record)
        attributes = self._format_extra_attributes(attributes=attributes)
        attributes = self._dict_to_str(attributes=attributes)

        # Call the parent format method so the final message is formed based on the "format"
        # attribute in the config
        msg = super(ConsoleLogFormatter, self).format(record)

        if attributes:
            msg = '%s (%s)' % (msg, attributes)

        return msg

    def _dict_to_str(self, attributes):
        result = []
        for key, value in six.iteritems(attributes):
            item = '%s=%s' % (key[1:], repr(value))
            result.append(item)

        result = ','.join(result)
        return result


class GelfLogFormatter(BaseExtraLogFormatter):
    """
    Formatter which formats messages as GELF 2 - https://www.graylog.org/resources/gelf-2/

    For example:

        LOG.info('Hello world', extra={'_id': 1, '_path': '/fooo'})

    Result:

        {
            "version": "1.1",
            "level": 6,
            "timestamp": 1426590583,
            "_python": {
                "process": 11277,
                "module": "__init__",
                "funcName": "db_setup",
                "processName": "MainProcess",
                "lineno": 28,
                "filename": "__init__.py"
            },
            "host": "vagrant-ubuntu-trusty-64",
            "full_message": "2015-03-17 11:09:43,507 INFO [-] Hello world",
            "_path": "/fooo",
            "_id": 1,
            "short_message": "Hello world"
        }
    """

    # Maps python log level to syslog / gelf log level
    PYTHON_TO_GELF_LEVEL_MAP = {
        50: 2,  # critical -> critical
        40: 3,  # error -> error
        30: 4,  # warning -> warning
        20: 6,  # info -> informational
        10: 7,  # debug -> debug
        0: 6,  # notset -> information
    }
    DEFAULT_LOG_LEVEL = 6  # info

    def format(self, record):
        attributes = self._get_extra_attributes(record=record)
        attributes = self._format_extra_attributes(attributes=attributes)

        msg = record.msg
        exc_info = record.exc_info
        now = int(time.time())
        level = self.PYTHON_TO_GELF_LEVEL_MAP.get(record.levelno, self.DEFAULT_LOG_LEVEL)

        common_attributes = self._get_common_extra_attributes(record=record)
        full_msg = super(GelfLogFormatter, self).format(record)

        data = {
            'version': GELF_SPEC_VERSION,
            'host': HOSTNAME,
            'short_message': msg,
            'full_message': full_msg,
            'timestamp': now,
            'level': level
        }

        if exc_info:
            # Include exception information
            exc_type, exc_value, exc_tb = exc_info
            tb_str = ''.join(traceback.format_tb(exc_tb))
            data['_exception'] = str(exc_value)
            data['_traceback'] = tb_str

        # Include common Python log record attributes
        data['_python'] = common_attributes

        # Include user extra attributes
        data.update(attributes)

        msg = json.dumps(data, cls=ObjectJSONEncoder)
        return msg
