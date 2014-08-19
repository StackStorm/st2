import glob
import json

from oslo.config import cfg

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.action import RunnerTypeAPI
from st2common.persistence.action import (RunnerType, Action)
from st2common.models.db.action import ActionDB
from st2common.util.action_db import get_runnertype_by_name


LOG = logging.getLogger(__name__)


def register_runner_types():
    RUNNER_TYPES = [
        {
            'name': 'shell',
            'description': 'A bash shell action type.',
            'enabled': True,
            'runner_parameters': {
                'hosts': {
                    'description': 'A comma delimited string of a list of hosts '
                                   'where the remote command will be executed.',
                    'type': 'string',
                    'default': 'localhost'
                },
                'cmd': {
                    'description': 'Arbitrary Linux command to be executed on the '
                                   'remote host(s).',
                    'type': 'string'
                },
                'parallel': {
                    'description': 'If true, the command will be executed on all the '
                                   'hosts in parallel.',
                    'type': 'boolean',
                    'default': False
                },
                'sudo': {
                    'description': 'The remote command will be executed with sudo.',
                    'type': 'boolean',
                    'default': False
                },
                'user': {
                    'description': 'The user who is executing this remote command. '
                                   'This is for audit purposes only. The remote '
                                   'command will always execute as the user stanley.',
                    'type': 'string'
                },
                'remotedir': {
                    'description': 'The working directory where the command will be '
                                   'executed on the remote host.',
                    'type': 'string'
                }
            },
            'required_parameters': ['cmd'],
            'runner_module': 'st2actionrunner.runners.fabricrunner'
        },
        {
            'name': 'remote-exec-sysuser',
            'description': 'A remote execution action type with a fixed system user.',
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
                'remotedir': {
                    'description': 'The working directory where the command will be '
                                   'executed on the remote host.',
                    'type': 'string'
                }
            },
            'required_parameters': ['hosts', 'cmd'],
            'runner_module': 'st2actionrunner.runners.fabricrunner'
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
            'runner_module': 'st2actionrunner.runners.httprunner'
        }
    ]

    LOG.debug('Registering runnertypes')

    for runnertype in RUNNER_TYPES:
        try:
            runnertype_db = get_runnertype_by_name(runnertype['name'])
            if runnertype_db:
                continue
        except StackStormDBObjectNotFoundError:
            LOG.debug('RunnerType "%s" does not exist in DB.', runnertype['name'])

        runnertype_api = RunnerTypeAPI(**runnertype)
        LOG.debug('RunnerType after field population: %s', runnertype_api)
        try:
            runnertype_db = RunnerType.add_or_update(RunnerTypeAPI.to_model(runnertype_api))
            LOG.debug('created runnertype name=%s in DB. Object: %s',
                      runnertype['name'], runnertype_db)
        except Exception as e:
            LOG.exception('Unable to register runner type %s. %s', runnertype['name'], e)

    LOG.debug('Registering runnertypes complete.')


def register_actions():
    actions = glob.glob(cfg.CONF.actions.modules_path + '/*.json')
    for action in actions:
        LOG.debug('Loading action from %s.', action)
        with open(action, 'r') as fd:
            try:
                content = json.load(fd)
            except ValueError:
                LOG.exception('Unable to load action from %s.', action)
                continue
            try:
                model = Action.get_by_name(str(content['name']))
            except ValueError:
                model = ActionDB()
            model.name = content['name']
            model.description = content['description']
            model.enabled = content['enabled']
            model.entry_point = content['entry_point']
            model.parameters = content.get('parameters', {})
            model.required_parameters = content.get('required_parameters', [])
            try:
                runnertype = get_runnertype_by_name(str(content['runner_type']))
                model.runner_type = {'name': runnertype.name}
            except StackStormDBObjectNotFoundError:
                LOG.exception('Failed to register action %s as runner %s was not found',
                              model.name, str(content['runner_type']))
                continue
            try:
                model = Action.add_or_update(model)
                LOG.debug('Added action %s from %s.', model.name, action)
            except Exception as e:
                LOG.exception('Failed to register action %s. %s', model.name, e)


def init_model():
    pass
