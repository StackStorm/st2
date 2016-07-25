__all__ = [
    'REMOTE_SHELL_CMD_EXECUTION_MODEL'
]

REMOTE_SHELL_CMD_EXECUTION_MODEL = {
    'action': {
        'ref': 'core.remote'
    },
    'context': {
        'user': 'st2admin'
    },
    'end_timestamp': '2016-07-25T21:07:33.957268Z',
    'id': '57967f9355fc8c19a96d9e4f',
    'liveaction': {
        'action': 'core.remote',
        'action_is_workflow': False,
        'callback': {},
        'id': '57967f9355fc8c19a96d9e4e',
        'notify': {
            'on-complete': {
                'data': {
                    'source_channel': 'chatops_ci',
                    'user': 'lakstorm'
                },
                'routes': [
                    'hubot'
                ]
            }
        },
        'parameters': {
            'cmd': 'date',
            'hosts': 'localhost'
        },
        'runner_info': {
            'hostname': 'st2test',
            'pid': 5686
        }
    },
    'parameters': {
        'cmd': 'date',
        'hosts': 'localhost'
    },
    'web_url': 'https://localhost.localdomain/#/history/57967f9355fc8c19a96d9e4f/general',
    'result': {
        'localhost': {
            'failed': False,
            'return_code': 0,
            'stderr': '',
            'stdout': 'Mon Jul 25 21:07:32 UTC 2016',
            'succeeded': True
        }
    },
    'start_timestamp': '2016-07-25T21:07:31.900544Z',
    'status': 'succeeded',
    'runner': {
        'enabled': True,
        'id': '54c6bb640640fd5211edef0b',
        'name': 'remote-shell-cmd',
        'runner_module': 'st2actions.runners.remote_command_runner',
        'runner_parameters': {
            'cmd': {
                'type': 'string'
            },
            'hosts': {
                'type': 'string'
            }
        }
    }
}
