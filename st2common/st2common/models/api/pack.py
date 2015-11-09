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

from st2common.models.api.base import BaseAPI
from st2common.models.db.pack import PackDB

__all__ = [
    'PackAPI'
]


class PackAPI(BaseAPI):
    model = PackDB
    schema = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string'
            },
            'ref': {
                'type': 'string'
            },
            "uid": {
                "type": "string"
            },
            'name': {
                'type': 'string',
                'required': True
            },
            'description': {
                'type': 'string'
            },
            'keywords': {
                'type': 'array',
                'items': {'type': 'string'},
                'default': []
            },
            'version': {
                'type': 'string'
            },
            'author': {
                'type': 'string'
            },
            'email': {
                'type': 'string'
            },
            'files': {
                'type': 'array',
                'items': {'type': 'string'},
                'default': []
            }
        },
        'additionalProperties': False
    }

    @classmethod
    def to_model(cls, pack):
        name = pack.name
        description = pack.description
        ref = pack.ref
        keywords = getattr(pack, 'keywords', [])
        version = str(pack.version)
        author = pack.author
        email = pack.email
        files = getattr(pack, 'files', [])

        model = cls.model(name=name, description=description, ref=ref, keywords=keywords,
                          version=version, author=author, email=email, files=files)

        return model
