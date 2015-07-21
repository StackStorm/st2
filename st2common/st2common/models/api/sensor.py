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
from st2common.models.db.sensor import SensorTypeDB, SensorInstanceDB, SensorExecutionDB
from st2common.models.utils import sensor_type_utils
from st2common.util import schema as util_schema


class SensorTypeAPI(BaseAPI):
    model = SensorTypeDB
    schema = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string',
                'default': None
            },
            'name': {
                'type': 'string',
                'required': True
            },
            'pack': {
                'type': 'string'
            },
            'description': {
                'type': 'string'
            },
            'artifact_uri': {
                'type': 'string',
            },
            'entry_point': {
                'type': 'string',
            },
            'enabled': {
                'description': 'Enable or disable the sensor.',
                'type': 'boolean',
                'default': True
            },
            'trigger_types': {
                'type': 'array',
                'default': []
            },
            'poll_interval': {
                'type': 'number'
            },
            'parameters_schema': {
                "description": "Input parameters for the sensor.",
                "type": "object",
                "patternProperties": {
                    "^\w+$": util_schema.get_draft_schema()
                },
                "default": {}
            }
        },
        'additionalProperties': False
    }

    @classmethod
    def to_model(cls, sensor_type):
        model = sensor_type_utils.to_sensor_db_model(sensor_api_model=sensor_type)
        return model


class SensorInstanceAPI(BaseAPI):
    model = SensorInstanceDB
    schema = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string',
                'default': None
            },
            'name': {
                'type': 'string',
                'required': True
            },
            'pack': {
                'type': 'string'
            },
            'description': {
                'type': 'string'
            },
            'sensor_type': {
                'type': 'string',
            },
            'enabled': {
                'description': 'Enable or disable the sensor.',
                'type': 'boolean',
                'default': True
            },
            'poll_interval': {
                'type': 'number'
            },
            "parameters": {
                "description": "Input parameters for the action.",
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
            },
        },
        'additionalProperties': False
    }

    @classmethod
    def to_model(cls, sensor_instance):
        model = sensor_type_utils.to_sensor_instance_db_model(
            sensor_instance_api_model=sensor_instance)
        return model


class SensorExecutionAPI(BaseAPI):
    model = SensorExecutionDB
    schema = {
        'type': 'object',
        'properties': {
            'id': {
                'type': 'string',
                'default': None
            },
            'status': {
                'type': 'string',
                'required': True
            },
            'sensor_node': {
                'type': 'string'
            },
            'sensor_instance': {
                'type': 'string'
            }
        },
        'additionalProperties': False
    }

    @classmethod
    def to_model(cls, sensor_execution):
        model = sensor_type_utils.to_sensor_execution_db_model(
            sensor_execution_api_model=sensor_execution)
        return model
