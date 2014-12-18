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


WEBHOOKS_PARAMETERS_SCHEMA = {
    'type': 'object',
    'properties': {
        'url': {
            'type': 'string'
        }
    },
    'required': [
        'url'
    ],
    'additionalProperties': False
}


WEBHOOKS_PAYLOAD_SCHEMA = {
    'type': 'object'
}

WEBHOOK_TRIGGER_TYPES = {
    ResourceReference.to_string_reference(SYSTEM_PACK_NAME, 'st2.webhook'): {
        'name': 'st2.webhook',
        'pack': SYSTEM_PACK_NAME,
        'description': 'Trigger type for registering webhooks that can consume'
                       + ' arbitrary payload.',
        'parameters_schema': WEBHOOKS_PARAMETERS_SCHEMA,
        'payload_schema': WEBHOOKS_PAYLOAD_SCHEMA
    }
}

# Timer specs

INTERVAL_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "timezone": {
            "type": "string"
        },
        "unit": {
            "enum": ["weeks", "days", "hours", "minutes", "seconds"]
        },
        "delta": {
            "type": "integer"
        }
    },
    "required": [
        "unit",
        "delta"
    ],
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
            "format": "date-time"
        }
    },
    "required": [
        "date"
    ],
    "additionalProperties": False
}

CRON_PARAMETERS_SCHEMA = {
    "type": "object",
    "properties": {
        "timezone": {
            "type": "string"
        },
        "year": {
            "type": "integer"
        },
        "month": {
            "type": "integer",
            "minimum": 1,
            "maximum": 12
        },
        "day": {
            "type": "integer",
            "minimum": 1,
            "maximum": 31
        },
        "week": {
            "type": "integer",
            "minimum": 1,
            "maximum": 53
        },
        "day_of_week": {
            "type": "integer",
            "minimum": 0,
            "maximum": 6
        },
        "hour": {
            "type": "integer",
            "minimum": 0,
            "maximum": 23
        },
        "minute": {
            "type": "integer",
            "minimum": 0,
            "maximum": 59
        },
        "second": {
            "type": "integer",
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

TIMER_TRIGGER_TYPES = {
    ResourceReference.to_string_reference(SYSTEM_PACK_NAME, 'st2.IntervalTimer'): {
        'name': 'st2.IntervalTimer',
        'pack': SYSTEM_PACK_NAME,
        'description': 'Triggers on specified intervals. e.g. every 30s, 1week etc.',
        'payload_schema': TIMER_PAYLOAD_SCHEMA,
        'parameters_schema': INTERVAL_PARAMETERS_SCHEMA
    },
    ResourceReference.to_string_reference(SYSTEM_PACK_NAME, 'st2.DateTimer'): {
        'name': 'st2.DateTimer',
        'pack': SYSTEM_PACK_NAME,
        'description': 'Triggers exactly once when the current time matches the specified time. '
                       'e.g. timezone:UTC date:2014-12-31 23:59:59.',
        'payload_schema': TIMER_PAYLOAD_SCHEMA,
        'parameters_schema': DATE_PARAMETERS_SCHEMA
    },
    ResourceReference.to_string_reference(SYSTEM_PACK_NAME, 'st2.CronTimer'): {
        'name': 'st2.CronTimer',
        'pack': SYSTEM_PACK_NAME,
        'description': 'Triggers whenever current time matches the specified time constaints like '
                       'a UNIX cron scheduler.',
        'payload_schema': TIMER_PAYLOAD_SCHEMA,
        'parameters_schema': CRON_PARAMETERS_SCHEMA
    }
}

SYSTEM_TRIGGER_TYPES = dict(WEBHOOK_TRIGGER_TYPES.items() + TIMER_TRIGGER_TYPES.items())
