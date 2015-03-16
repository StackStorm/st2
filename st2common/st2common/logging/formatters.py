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

import six

__all__ = [
    'ConsoleLogFormatter',
    'GelfLogFormatter'
]

HOSTNAME = socket.gethostname()
COMMON_ATTRIBUTE_NAMES = [
    'process',
    'module',
    'filename',
    'funcName',
    'lineno'
    'processName',
]


class BaseExtraLogFormatter(logging.Formatter):
    def _get_extra_attributes(self, record):
        attributes = dict([(k, v) for k, v in six.iteritems(record.__dict__)
                           if k.startswith('_')])
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
        simple_types = (list, dict, int, float) + six.string_types

        result = {}
        for key, value in six.iteritems(attributes):
            if isinstance(value, simple_types):
                # Leave simple types as is
                value = value
            elif isinstance(value, object):
                if getattr(value, 'to_dict', None):
                    # Check for a custom serialization method
                    value = value.to_dict()
                else:
                    value = repr(value)

            result[key] = value

        return result


class ConsoleLogFormatter(BaseExtraLogFormatter):
    """
    Custom log formatter which attaches all the attributes from the "extra"
    dictionary which start with an underscore to the end of the log message.
    For example:
    extra={'_id': 'user-1', '_path': '/foo/bar'}
    """

    def format(self, record):
        attributes = self._get_extra_attributes(record=record)
        attributes = self._format_extra_attributes(attributes=attributes)
        attributes = self._dict_to_str(attributes=attributes)

        msg = super(ConsoleLogFormatter, self).format(record)
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
    """
    def format(self, record):
        attributes = self._get_extra_attributes(record=record)
        attributes = self._format_extra_attributes(attributes=attributes)

        msg = record.msg
        now = int(time.time())

        common_attributes = self._get_common_extra_attributes(record=record)

        data = {
            'version': '1.1',
            'host': HOSTNAME,
            'short_message': msg,
            'full_message': msg,
            'timestamp': now,
            'level': record.levelno
        }
        data['_python'] = common_attributes
        data.update(attributes)

        msg = json.dumps(data)
        return msg
