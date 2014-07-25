import glob
import json

from oslo.config import cfg

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.action import ActionTypeAPI
from st2common.persistence.action import (ActionType, Action)
from st2common.models.db.action import ActionDB
from st2common.util.action_db import get_actiontype_by_name

LOG = logging.getLogger(__name__)


def register_action_types():
    ACTION_TYPES = [{'name': 'internaldummy-builtin',
                     'description': ('An built-in, internal action type for development only.'),
                     'enabled': True,
                     'runner_parameters': {'command': None},
                     'runner_module': 'no.such.module'},

                    {'name': 'internaldummy',
                      'description': ('An internal action type for development only. Implemented '
                                      'using a plugin.'),
                      'enabled': True,
                      'runner_parameters': {'command': None},
                      'runner_module': 'st2actionrunner.runners.internaldummy'},

                    {'name': 'shell',
                     'description': 'A bash shell action type.',
                     'enabled': True,
                     'runner_parameters': {'shell': '/usr/bin/bash',
                                           'args': None},
                     'runner_module': 'st2actionrunner.runners.shellrunner'},

                     {'name': 'remote-exec-sysuser',
                      'description': 'A remote execution action type with a fixed system user.',
                      'enabled': True,
                      'runner_parameters': {'hosts': None,
                                            'parallel': None,
                                            'sudo': None,
                                            'user': None,
                                            'command': None,
                                            'remotedir': None},
                      'runner_module': 'st2actionrunner.runners.fabricrunner'}]

    LOG.debug('Registering actiontypes')

    for fields in ACTION_TYPES:
        actiontype_db = None
        name = fields['name']
        try:
            actiontype_db = get_actiontype_by_name(name)
        except StackStormDBObjectNotFoundError:
            LOG.debug('ActionType "%s" does not exist in DB', name)
        else:
            continue

        if actiontype_db is None:
            actiontype = ActionTypeAPI()
            for (key, value) in fields.items():
                LOG.debug('actiontype name=%s field=%s value=%s', name, key, value)
                setattr(actiontype, key, value)

            actiontype_api = ActionTypeAPI.to_model(actiontype)
            LOG.debug('ActionType after field population: %s', actiontype_api)
            actiontype_db = ActionType.add_or_update(actiontype_api)
            LOG.debug('created actiontype name=%s in DB. Object: %s', name, actiontype_db)

    LOG.debug('Registering actiontypes complete')

def register_actions():
    actions = glob.glob(cfg.CONF.actions.modules_path + '/*.json')
    for action in actions:
        with open(action, 'r') as fd:
            content = json.load(fd)
            try:
                model = Action.get_by_name(str(content['name']))
            except:
                model = ActionDB()
            model.name = str(content['name'])
            model.description = str(content['description'])
            model.enabled = bool(content['enabled'])
            model.artifact_paths = [str(v) for v in content['artifact_paths']]
            model.entry_point = str(content['entry_point'])
            model.runner_type = str(content['runner_type'])
            model.parameters = dict(content['parameters'])
            model = Action.add_or_update(model)

def init_model():
    pass
