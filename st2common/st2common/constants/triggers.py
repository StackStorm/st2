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

from st2common.constants.pack import SYSTEM_PACK_NAME
from st2common.models.system.common import ResourceReference

__all__ = [
    'WEBHOOKS_PARAMETERS_SCHEMA',
    'WEBHOOKS_PAYLOAD_SCHEMA',
    'INTERVAL_PARAMETERS_SCHEMA',
    'DATE_PARAMETERS_SCHEMA',
    'CRON_PARAMETERS_SCHEMA',
    'TIMER_PAYLOAD_SCHEMA',

    'ACTION_SENSOR_TRIGGER',
    'NOTIFY_TRIGGER',
    'ACTION_FILE_WRITTEN_TRIGGER',

    'TIMER_TRIGGER_TYPES',
    'WEBHOOK_TRIGGER_TYPES',
    'WEBHOOK_TRIGGER_TYPE',
    'INTERNAL_TRIGGER_TYPES',
    'SYSTEM_TRIGGER_TYPES',

    'INTERVAL_TIMER_TRIGGER_REF',
    'DATE_TIMER_TRIGGER_REF',
    'CRON_TIMER_TRIGGER_REF',

    'TRIGGER_INSTANCE_STATUSES',
    'TRIGGER_INSTANCE_PENDING',
    'TRIGGER_INSTANCE_PROCESSING',
    'TRIGGER_INSTANCE_PROCESSED',
    'TRIGGER_INSTANCE_PROCESSING_FAILED'
]

# Action resource triggers
ACTION_SENSOR_TRIGGER = {
    'name': 'st2.generic.actiontrigger',
    'pack': SYSTEM_PACK_NAME,
    'description': 'Trigger encapsulating the completion of an action execution.',
    'payload_schema': {
        'type': 'object',
        'properties': {
            'execution_id': {},
            'status': {},
            'start_timestamp': {},
            'action_name': {},
            'parameters': {},
            'result': {}
        }
    }
}
ACTION_FILE_WRITTEN_TRIGGER = {
    'name': 'st2.action.file_writen',
    'pack': SYSTEM_PACK_NAME,
    'description': 'Trigger encapsulating action file being written on disk.',
    'payload_schema': {
        'type': 'object',
        'properties': {
            'ref': {},
            'file_path': {},
            'content': {},
            'host_info': {}
        }
    }
}

NOTIFY_TRIGGER = {
    'name': 'st2.generic.notifytrigger',
    'pack': SYSTEM_PACK_NAME,
    'description': 'Notification trigger.',
    'payload_schema': {
        'type': 'object',
        'properties': {
            'execution_id': {},
            'status': {},
            'start_timestamp': {},
            'end_timestamp': {},
            'action_ref': {},
            'channel': {},
            'message': {},
            'data': {}
        }
    }
}

# Sensor spawn/exit triggers.
SENSOR_SPAWN_TRIGGER = {
    'name': 'st2.sensor.process_spawn',
    'pack': SYSTEM_PACK_NAME,
    'description': 'Trigger indicating sensor process is started up.',
    'payload_schema': {
        'type': 'object',
        'properties': {
            'object': {}
        }
    }
}

SENSOR_EXIT_TRIGGER = {
    'name': 'st2.sensor.process_exit',
    'pack': SYSTEM_PACK_NAME,
    'description': 'Trigger indicating sensor process is stopped.',
    'payload_schema': {
        'type': 'object',
        'properties': {
            'object': {}
        }
    }
}

# KeyValuePair resource triggers
KEY_VALUE_PAIR_CREATE_TRIGGER = {
    'name': 'st2.key_value_pair.create',
    'pack': SYSTEM_PACK_NAME,
    'description': 'Trigger encapsulating datastore item creation.',
    'payload_schema': {
        'type': 'object',
        'properties': {
            'object': {}
        }
    }
}

KEY_VALUE_PAIR_UPDATE_TRIGGER = {
    'name': 'st2.key_value_pair.update',
    'pack': SYSTEM_PACK_NAME,
    'description': 'Trigger encapsulating datastore set action.',
    'payload_schema': {
        'type': 'object',
        'properties': {
            'object': {}
        }
    }
}

KEY_VALUE_PAIR_VALUE_CHANGE_TRIGGER = {
    'name': 'st2.key_value_pair.value_change',
    'pack': SYSTEM_PACK_NAME,
    'description': 'Trigger encapsulating a change of datastore item value.',
    'payload_schema': {
        'type': 'object',
        'properties': {
            'old_object': {},
            'new_object': {}
        }
    }
}

KEY_VALUE_PAIR_DELETE_TRIGGER = {
    'name': 'st2.key_value_pair.delete',
    'pack': SYSTEM_PACK_NAME,
    'description': 'Trigger encapsulating datastore item deletion.',
    'payload_schema': {
        'type': 'object',
        'properties': {
            'object': {}
        }
    }
}

# Internal system triggers which are available for each resource
INTERNAL_TRIGGER_TYPES = {
    'action': [
        ACTION_SENSOR_TRIGGER,
        NOTIFY_TRIGGER,
        ACTION_FILE_WRITTEN_TRIGGER
    ],
    'sensor': [
        SENSOR_SPAWN_TRIGGER,
        SENSOR_EXIT_TRIGGER
    ],
    'key_value_pair': [
        KEY_VALUE_PAIR_CREATE_TRIGGER,
        KEY_VALUE_PAIR_UPDATE_TRIGGER,
        KEY_VALUE_PAIR_VALUE_CHANGE_TRIGGER,
        KEY_VALUE_PAIR_DELETE_TRIGGER
    ]
}


WEBHOOKS_PARAMETERS_SCHEMA = {
    'type': 'object',
    'properties': {
        'url': {
            'type': 'string',
            'required': True
        }
    },
    'additionalProperties': False
}


WEBHOOKS_PAYLOAD_SCHEMA = {
    'type': 'object'
}

WEBHOOK_TRIGGER_TYPES = {
    ResourceReference.to_string_reference(SYSTEM_PACK_NAME, 'st2.webhook'): {
        'name': 'st2.webhook',
        'pack': SYSTEM_PACK_NAME,
        'description': ('Trigger type for registering webhooks that can consume'
                        ' arbitrary payload.'),
        'parameters_schema': WEBHOOKS_PARAMETERS_SCHEMA,
        'payload_schema': WEBHOOKS_PAYLOAD_SCHEMA
    }
}
WEBHOOK_TRIGGER_TYPE = WEBHOOK_TRIGGER_TYPES.keys()[0]

# Timer specs

INTERVAL_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "timezone": {
            "type": "string"
        },
        "unit": {
            "enum": ["weeks", "days", "hours", "minutes", "seconds"],
            "required": True
        },
        "delta": {
            "type": "integer",
            "required": True

        }
    },
    "additionalProperties": False
}

DATE_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "timezone": {
            "type": "string"
        },
        "date": {
            "type": "string",
            "format": "date-time",
            "required": True
        }
    },
    "additionalProperties": False
}

CRON_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "timezone": {
            "type": "string"
        },
        "year": {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"}
            ],
        },
        "month": {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"}
            ],
            "minimum": 1,
            "maximum": 12
        },
        "day": {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"}
            ],
            "minimum": 1,
            "maximum": 31
        },
        "week": {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"}
            ],
            "minimum": 1,
            "maximum": 53
        },
        "day_of_week": {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"}
            ],
            "minimum": 0,
            "maximum": 6
        },
        "hour": {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"}
            ],
            "minimum": 0,
            "maximum": 23
        },
        "minute": {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"}
            ],
            "minimum": 0,
            "maximum": 59
        },
        "second": {
            "anyOf": [
                {"type": "string"},
                {"type": "integer"}
            ],
            "minimum": 0,
            "maximum": 59
        }
    },
    "additionalProperties": False
}

TIMER_PAYLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "executed_at": {
            "type": "string",
            "format": "date-time",
            "default": "2014-07-30 05:04:24.578325"
        },
        "schedule": {
            "type": "object",
            "default": {
                "delta": 30,
                "units": "seconds"
            }
        }
    }
}

INTERVAL_TIMER_TRIGGER_REF = ResourceReference.to_string_reference(SYSTEM_PACK_NAME,
                                                                   'st2.IntervalTimer')
DATE_TIMER_TRIGGER_REF = ResourceReference.to_string_reference(SYSTEM_PACK_NAME, 'st2.DateTimer')
CRON_TIMER_TRIGGER_REF = ResourceReference.to_string_reference(SYSTEM_PACK_NAME, 'st2.CronTimer')

TIMER_TRIGGER_TYPES = {
    INTERVAL_TIMER_TRIGGER_REF: {
        'name': 'st2.IntervalTimer',
        'pack': SYSTEM_PACK_NAME,
        'description': 'Triggers on specified intervals. e.g. every 30s, 1week etc.',
        'payload_schema': TIMER_PAYLOAD_SCHEMA,
        'parameters_schema': INTERVAL_PARAMETERS_SCHEMA
    },
    DATE_TIMER_TRIGGER_REF: {
        'name': 'st2.DateTimer',
        'pack': SYSTEM_PACK_NAME,
        'description': 'Triggers exactly once when the current time matches the specified time. '
                       'e.g. timezone:UTC date:2014-12-31 23:59:59.',
        'payload_schema': TIMER_PAYLOAD_SCHEMA,
        'parameters_schema': DATE_PARAMETERS_SCHEMA
    },
    CRON_TIMER_TRIGGER_REF: {
        'name': 'st2.CronTimer',
        'pack': SYSTEM_PACK_NAME,
        'description': 'Triggers whenever current time matches the specified time constaints like '
                       'a UNIX cron scheduler.',
        'payload_schema': TIMER_PAYLOAD_SCHEMA,
        'parameters_schema': CRON_PARAMETERS_SCHEMA
    }
}

SYSTEM_TRIGGER_TYPES = dict(WEBHOOK_TRIGGER_TYPES.items() + TIMER_TRIGGER_TYPES.items())

# various status to record lifecycle of a TriggerInstance
TRIGGER_INSTANCE_PENDING = 'pending'
TRIGGER_INSTANCE_PROCESSING = 'processing'
TRIGGER_INSTANCE_PROCESSED = 'processed'
TRIGGER_INSTANCE_PROCESSING_FAILED = 'processing_failed'


TRIGGER_INSTANCE_STATUSES = [
    TRIGGER_INSTANCE_PENDING,
    TRIGGER_INSTANCE_PROCESSING,
    TRIGGER_INSTANCE_PROCESSED,
    TRIGGER_INSTANCE_PROCESSING_FAILED
]
