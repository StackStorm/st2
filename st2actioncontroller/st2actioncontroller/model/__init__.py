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
    RUNNER_TYPES = [{'name': 'shell',
                     'description': 'A bash shell action type.',
                     'enabled': True,
                     'runner_parameters': {'hosts': 'localhost',
                                           'parallel': 'False',
                                           'sudo': 'False',
                                           'user': None,
                                           'cmd': None,
                                           'remotedir': None},
                     'runner_module': 'st2actionrunner.runners.fabricrunner'},

                    {'name': 'remote-exec-sysuser',
                     'description': 'A remote execution action type with a fixed system user.',
                     'enabled': True,
                     'runner_parameters': {'hosts': None,
                                           'parallel': None,
                                           'sudo': None,
                                           'user': None,
                                           'cmd': None,
                                           'remotedir': None},
                     'runner_module': 'st2actionrunner.runners.fabricrunner'},

                    {'name': 'http-runner',
                     'description': 'A HTTP client for running HTTP actions.',
                     'enabled': True,
                     'runner_parameters': {'url': None,
                                           'headers': None,
                                           'cookies': None,
                                           'proxy': None,
                                           'redirects': None},
                     'runner_module': 'st2actionrunner.runners.httprunner'}]

    LOG.debug('Registering runnertypes')

    for fields in RUNNER_TYPES:
        runnertype_db = None
        name = fields['name']
        try:
            runnertype_db = get_runnertype_by_name(name)
        except StackStormDBObjectNotFoundError:
            LOG.debug('RunnerType "%s" does not exist in DB', name)
        else:
            continue

        if runnertype_db is None:
            runnertype = RunnerTypeAPI()
            for (key, value) in fields.items():
                LOG.debug('runnertype name=%s field=%s value=%s', name, key, value)
                setattr(runnertype, key, value)

            runnertype_api = RunnerTypeAPI.to_model(runnertype)
            LOG.debug('RunnerType after field population: %s', runnertype_api)
            try:
                runnertype_db = RunnerType.add_or_update(runnertype_api)
                LOG.debug('created runnertype name=%s in DB. Object: %s', name, runnertype_db)
            except:
                LOG.exception('Unable to register runner type %s.', runnertype['name'])

    LOG.debug('Registering runnertypes complete')


def register_actions():
    actions = glob.glob(cfg.CONF.actions.modules_path + '/*.json')
    for action in actions:
        LOG.debug('Loading action from %s', action)
        with open(action, 'r') as fd:
            try:
                content = json.load(fd)
            except:
                LOG.exception('Unable to load action from %s.', action)
                continue
            try:
                model = Action.get_by_name(str(content['name']))
            except:
                model = ActionDB()
            model.name = str(content['name'])
            model.description = str(content['description'])
            model.enabled = bool(content['enabled'])
            model.entry_point = str(content['entry_point'])
            try:
                model.runner_type = get_runnertype_by_name(str(content['runner_type']))
            except StackStormDBObjectNotFoundError:
                LOG.exception('Failed to register action %s as runner %s was not found',
                              model.name, str(content['runner_type']))
                continue
            model.parameters = dict(content['parameters'])
            model = Action.add_or_update(model)
            LOG.debug('Added action %s from %s.', model.name, action)


def init_model():
    pass
