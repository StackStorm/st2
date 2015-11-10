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
from st2common.models.db.policy import PolicyTypeDB, PolicyDB
from st2common import log as logging
from st2common.util import schema as util_schema


__all__ = ['PolicyTypeAPI']

LOG = logging.getLogger(__name__)


class PolicyTypeAPI(BaseAPI):
    model = PolicyTypeDB
    schema = {
        "title": "Policy Type",
        "type": "object",
        "properties": {
            "id": {
                "type": "string"
            },
            "name": {
                "type": "string",
                "required": True
            },
            "resource_type": {
                "enum": ["action"],
                "required": True
            },
            "ref": {
                "type": "string"
            },
            "description": {
                "type": "string"
            },
            "enabled": {
                "type": "boolean",
                "default": True
            },
            "module": {
                "type": "string",
                "required": True
            },
            "parameters": {
                "type": "object",
                "patternProperties": {
                    "^\w+$": util_schema.get_draft_schema()
                }
            }
        },
        "additionalProperties": False
    }

    @classmethod
    def to_model(cls, instance):
        return cls.model(name=str(instance.name),
                         description=getattr(instance, 'description', None),
                         resource_type=str(instance.resource_type),
                         ref=getattr(instance, 'ref', None),
                         enabled=getattr(instance, 'enabled', None),
                         module=str(instance.module),
                         parameters=getattr(instance, 'parameters', dict()))


class PolicyAPI(BaseAPI):
    model = PolicyDB
    schema = {
        "title": "Policy",
        "type": "object",
        "properties": {
            "id": {
                "type": "string"
            },
            "name": {
                "type": "string",
                "required": True
            },
            "pack": {
                "type": "string"
            },
            "ref": {
                "type": "string"
            },
            "description": {
                "type": "string"
            },
            "enabled": {
                "type": "boolean",
                "default": True
            },
            "resource_ref": {
                "type": "string",
                "required": True
            },
            "policy_type": {
                "type": "string",
                "required": True
            },
            "parameters": {
                "type": "object",
                "patternProperties": {
                    "^\w+$": {
                        "anyOf": [
                            {"type": "array"},
                            {"type": "boolean"},
                            {"type": "integer"},
                            {"type": "number"},
                            {"type": "object"},
                            {"type": "string"}
                        ]
                    }
                }
            }
        },
        "additionalProperties": False
    }

    @classmethod
    def to_model(cls, instance):
        return cls.model(id=getattr(instance, 'id', None),
                         name=str(instance.name),
                         description=getattr(instance, 'description', None),
                         pack=str(instance.pack),
                         ref=getattr(instance, 'ref', None),
                         enabled=getattr(instance, 'enabled', None),
                         resource_ref=str(instance.resource_ref),
                         policy_type=str(instance.policy_type),
                         parameters=getattr(instance, 'parameters', dict()))
