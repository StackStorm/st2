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

"""
Module containing model UID related utility functions.
"""

from st2common.models.db.stormbase import UIDFieldMixin

__all__ = [
    'parse_uid'
]


def parse_uid(uid):
    """
    Parse UID string.

    :return: (ResourceType, uid_remainder)
    :rtype: ``tuple``
    """
    if UIDFieldMixin.UID_SEPARATOR not in uid:
        raise ValueError('Invalid uid: %s' % (uid))

    parsed = uid.split(UIDFieldMixin.UID_SEPARATOR)

    if len(parsed) < 2:
        raise ValueError('Invalid or malformed uid: %s' % (uid))

    resource_type = parsed[0]
    uid_remainder = parsed[1:]

    return (resource_type, uid_remainder)
