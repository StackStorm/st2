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

import datetime

import six

from st2common.util import isotime
from st2common.util import date as date_utils
from st2common.models.api.base import BaseAPI
from st2common.models.db.keyvalue import KeyValuePairDB


class KeyValuePairAPI(BaseAPI):
    model = KeyValuePairDB
    schema = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string'
            },
            'name': {
                'type': 'string'
            },
            'description': {
                'type': 'string'
            },
            'value': {
                'type': 'string',
                'required': True
            },
            'expire_timestamp': {
                'type': 'string',
                'pattern': isotime.ISO8601_UTC_REGEX
            },
            # Note: Those values are only used for input
            # TODO: Improve
            'ttl': {
                'type': 'integer'
            }
        },
        'additionalProperties': False
    }

    @classmethod
    def from_model(cls, model, mask_secrets=False):
        doc = cls._from_model(model, mask_secrets=mask_secrets)

        if 'id' in doc:
            del doc['id']

        if model.expire_timestamp:
            doc['expire_timestamp'] = isotime.format(model.expire_timestamp, offset=False)

        attrs = {attr: value for attr, value in six.iteritems(doc) if value is not None}
        return cls(**attrs)

    @classmethod
    def to_model(cls, kvp):
        name = getattr(kvp, 'name', None)
        description = getattr(kvp, 'description', None)
        value = kvp.value

        if getattr(kvp, 'ttl', None):
            expire_timestamp = (date_utils.get_datetime_utc_now() +
                                datetime.timedelta(seconds=kvp.ttl))
        else:
            expire_timestamp = None

        model = cls.model(name=name, description=description, value=value,
                          expire_timestamp=expire_timestamp)

        return model
