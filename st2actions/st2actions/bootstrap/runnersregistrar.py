from oslo.config import cfg

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.action import RunnerTypeAPI
from st2common.persistence.action import RunnerType
from st2common.util.action_db import get_runnertype_by_name


LOG = logging.getLogger(__name__)


def register_runner_types():
    try:
        default_remote_dir = cfg.CONF.ssh_runner.remote_dir
    except:
        default_remote_dir = '/tmp'

    RUNNER_TYPES = [
        {
            'name': 'run-local',
            'description': 'A runner to execute local actions as a fixed user.',
            'enabled': True,
            'runner_parameters': {
                'hosts': {
                    'description': 'Fixed to localhost as this action is run locally.',
                    'type': 'string',
                    'default': 'localhost',
                    'immutable': True
                },
                'cmd': {
                    'description': 'Arbitrary Linux command to be executed on the '
                                   'host.',
                    'type': 'string'
                },
                'parallel': {
                    'description': 'Parallel execution is unsupported.',
                    'type': 'boolean',
                    'default': False,
                    'immutable': True
                },
                'sudo': {
                    'description': 'The command will be executed with sudo.',
                    'type': 'boolean',
                    'default': False
                },
                'user': {
                    'description': 'The user who is executing this command. '
                                   'This is for audit purposes only. The '
                                   'command will always execute as the user stanley.',
                    'type': 'string'
                },
                'dir': {
                    'description': 'The working directory where the command will be '
                                   'executed on the host.',
                    'type': 'string',
                    'default': default_remote_dir
                },
                'kwarg_op': {
                    'description': 'Operator to use in front of keyword args i.e. "--" or "-".',
                    'type': 'string',
                    'default': '--'
                }
            },
            'runner_module': 'st2actions.runners.fabricrunner'
        },
        {
            'name': 'run-local-script',
            'description': 'A runner to execute local actions as a fixed user.',
            'enabled': True,
            'runner_parameters': {
                'hosts': {
                    'description': 'Fixed to localhost as this action is run locally.',
                    'type': 'string',
                    'default': 'localhost',
                    'immutable': True
                },
                'parallel': {
                    'description': 'Parallel execution is unsupported.',
                    'type': 'boolean',
                    'default': False,
                    'immutable': True
                },
                'sudo': {
                    'description': 'The command will be executed with sudo.',
                    'type': 'boolean',
                    'default': False
                },
                'user': {
                    'description': 'The user who is executing this command. '
                                   'This is for audit purposes only. The '
                                   'command will always execute as the user stanley.',
                    'type': 'string'
                },
                'dir': {
                    'description': 'The working directory where the command will be '
                                   'executed on the host.',
                    'type': 'string',
                    'default': default_remote_dir
                },
                'kwarg_op': {
                    'description': 'Operator to use in front of keyword args i.e. "--" or "-".',
                    'type': 'string',
                    'default': '--'
                }
            },
            'runner_module': 'st2actions.runners.fabricrunner'
        },
        {
            'name': 'run-remote',
            'description': 'A remote execution runner that executes actions '
                           'as a fixed system user.',
            'enabled': True,
            'runner_parameters': {
                'hosts': {
                    'description': 'A comma delimited string of a list of hosts '
                                   'where the remote command will be executed.',
                    'type': 'string'
                },
                'cmd': {
                    'description': 'Arbitrary Linux command to be executed on the '
                                   'remote host(s).',
                    'type': 'string'
                },
                'parallel': {
                    'description': 'If true, the command will be executed on all the '
                                   'hosts in parallel.',
                    'type': 'boolean'
                },
                'sudo': {
                    'description': 'The remote command will be executed with sudo.',
                    'type': 'boolean'
                },
                'user': {
                    'description': 'The user who is executing this remote command. '
                                   'This is for audit purposes only. The remote '
                                   'command will always execute as the user stanley.',
                    'type': 'string'
                },
                'dir': {
                    'description': 'The working directory where the command will be '
                                   'executed on the remote host.',
                    'type': 'string',
                    'default': default_remote_dir
                },
                'kwarg_op': {
                    'description': 'Operator to use in front of keyword args i.e. "--" or "-".',
                    'type': 'string',
                    'default': '--'
                }
            },
            'required_parameters': ['hosts'],
            'runner_module': 'st2actions.runners.fabricrunner'
        },
        {
            'name': 'run-remote-script',
            'description': 'A remote execution runner that executes actions '
                           'as a fixed system user.',
            'enabled': True,
            'runner_parameters': {
                'hosts': {
                    'description': 'A comma delimited string of a list of hosts '
                                   'where the remote command will be executed.',
                    'type': 'string'
                },
                'parallel': {
                    'description': 'If true, the command will be executed on all the '
                                   'hosts in parallel.',
                    'type': 'boolean'
                },
                'sudo': {
                    'description': 'The remote command will be executed with sudo.',
                    'type': 'boolean'
                },
                'user': {
                    'description': 'The user who is executing this remote command. '
                                   'This is for audit purposes only. The remote '
                                   'command will always execute as the user stanley.',
                    'type': 'string'
                },
                'dir': {
                    'description': 'The working directory where the command will be '
                                   'executed on the remote host.',
                    'type': 'string',
                    'default': default_remote_dir
                },
                'kwarg_op': {
                    'description': 'Operator to use in front of keyword args i.e. "--" or "-".',
                    'type': 'string',
                    'default': '--'
                }
            },
            'required_parameters': ['hosts'],
            'runner_module': 'st2actions.runners.fabricrunner'
        },
        {
            'name': 'http-runner',
            'description': 'A HTTP client for running HTTP actions.',
            'enabled': True,
            'runner_parameters': {
                'url': {
                    'description': 'URL to the HTTP endpoint.',
                    'type': 'string'
                },
                'headers': {
                    'description': 'HTTP headers for the request.',
                    'type': 'object'
                },
                'cookies': {
                    'description': 'TODO: Description for cookies.',
                    'type': 'string'
                },
                'proxy': {
                    'description': 'TODO: Description for proxy.',
                    'type': 'string'
                },
                'redirects': {
                    'description': 'TODO: Description for redirects.',
                    'type': 'string'
                },
            },
            'required_parameters': ['url'],
            'runner_module': 'st2actions.runners.httprunner'
        },
        {
            'name': 'workflow',
            'description': 'A runner for launching workflow actions.',
            'enabled': True,
            'runner_parameters': {
                'workbook': {
                    'description': 'The name of the workbook.',
                    'type': 'string'
                },
                'task': {
                    'description': 'The startup task in the workbook to execute.',
                    'type': 'string'
                },
                'context': {
                    'description': 'Context for the startup task.',
                    'type': 'object',
                    'default': {}
                }
            },
            'runner_module': 'st2actions.runners.mistral'
        },
        {
            'name': 'action-chain',
            'description': 'A runner for launching linear action chains.',
            'enabled': True,
            'runner_parameters': {},
            'runner_module': 'st2actions.runners.actionchainrunner'
        }
    ]

    LOG.info('Start : register default RunnerTypes.')

    for runnertype in RUNNER_TYPES:
        try:
            runnertype_db = get_runnertype_by_name(runnertype['name'])
            if runnertype_db:
                LOG.info('RunnerType name=%s exists.', runnertype['name'])
                continue
        except StackStormDBObjectNotFoundError:
            pass

        runnertype_api = RunnerTypeAPI(**runnertype)
        try:
            runnertype_db = RunnerType.add_or_update(RunnerTypeAPI.to_model(runnertype_api))
            LOG.audit('RunnerType created. RunnerType %s', runnertype_db)
        except Exception:
            LOG.exception('Unable to register runner type %s.', runnertype['name'])

    LOG.info('End : register default RunnerTypes.')
