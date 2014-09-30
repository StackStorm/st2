import bson
import copy


TRIGGER_TYPE = {
    'id': str(bson.ObjectId()),
    'payload_schema': {
        'type': 'object'
    },
    'parameters_schema': {
        'additionalProperties': False,
        'required': [
            'url'
        ],
        'type': 'object',
        'properties': {
            'url': {
                'type': 'string'
            }
        }
    },
    'name': 'st2.webhook',
}

TRIGGER = {
    'id': str(bson.ObjectId()),
    'name': '46f67652-20cd-4bab-94e2-4615baa846d0',
    'type': 'st2.webhook',
    'parameters': {
        'url': 'person'
    }
}

TRIGGER_INSTANCE = {
    'id': str(bson.ObjectId()),
    'trigger': '46f67652-20cd-4bab-94e2-4615baa846d0',
    'payload': {
        'foo': 'bar',
        'name': 'Joe'
    },
    'occurrence_time': '2014-09-01 00:00:01.000000'
}

RUNNER_TYPE = {
    'id': str(bson.ObjectId()),
    'name': 'run-local',
    'description': 'A runner to execute local actions as a fixed user.',
    'enabled': True,
    'runner_parameters': {
        'hosts': {
            'type': 'string',
            'default': 'localhost'
        },
        'cmd': {
            'type': 'string'
        },
        'parallel': {
            'type': 'boolean',
            'default': False
        },
        'sudo': {
            'type': 'boolean',
            'default': False
        },
        'user': {
            'type': 'string'
        },
        'dir': {
            'type': 'string'
        }
    },
    'runner_module': 'st2actions.runners.fabricrunner'
}

RULE = {
    'id': str(bson.ObjectId()),
    'enabled': True,
    'trigger': {
        'type': 'st2.webhook',
        'description': '',
        'parameters': {
            'url': 'person'
        }
    },
    'criteria': {
        'trigger.name': {
            'pattern': 'Joe',
            'type': 'equals'
        }
    },
    'action': {
        'name': 'local',
        'parameters': {
            'cmd': 'echo "{{trigger}}" >> /tmp/st2.persons.out'
        }
    },
    'name': 'st2.person.joe'
}

ACTION = {
    'id': str(bson.ObjectId()),
    'runner_type': 'run-local',
    'name': 'local',
    'enabled': True,
    'content_pack': 'core'
}

ACTION_EXECUTION = {
    'id': str(bson.ObjectId()),
    'status': 'succeeded',
    'start_timestamp': '2014-09-01 00:00:02.000000',
    'parameters': {
        'cmd': 'echo "{u\'foo\': u\'bar\', u\'name\': u\'Joe\'}" >> /tmp/st2.persons.out',
        'hosts': 'localhost',
        'sudo': False,
        'parallel': False
    },
    'callback': {},
    'result': {
        'localhost': {
            'failed': False,
            'stderr': '',
            'return_code': 0,
            'succeeded': True,
            'stdout': ''
        }
    },
    'context': {
        'user': 'system'
    },
    'action': {
        'name': 'local'
    }
}

ACTION_EXECUTION_HISTORY = {
    'id': str(bson.ObjectId()),
    'trigger': copy.deepcopy(TRIGGER),
    'trigger_type': copy.deepcopy(TRIGGER_TYPE),
    'trigger_instance': copy.deepcopy(TRIGGER_INSTANCE),
    'rule': copy.deepcopy(RULE),
    'action': copy.deepcopy(ACTION),
    'runner_type': copy.deepcopy(RUNNER_TYPE),
    'execution': copy.deepcopy(ACTION_EXECUTION)
}
