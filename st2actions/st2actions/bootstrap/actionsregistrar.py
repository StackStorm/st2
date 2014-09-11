import glob
import json

from oslo.config import cfg

from st2common import log as logging
from st2common.content.loader import ContentPackLoader
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.action import Action
from st2common.models.db.action import ActionDB
from st2common.util.action_db import get_runnertype_by_name

LOG = logging.getLogger(__name__)


def _get_actions_from_pack(pack):
    return glob.glob(pack + '/*.json')


def _register_actions_from_pack(pack, actions):
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
            pack_name = content.get('pack', None)
            if not pack_name or pack_name == '':
                pack_name = pack
                LOG.warning('Pack name missing. Using: %s', pack_name)
            model.content_pack = pack_name
            model.entry_point = content['entry_point']
            model.parameters = content.get('parameters', {})
            model.required_parameters = content.get('required_parameters', [])
            try:
                runner_type = get_runnertype_by_name(str(content['runner_type']))
                model.runner_type = {'name': runner_type.name}
            except StackStormDBObjectNotFoundError:
                LOG.exception('Failed to register action %s as runner %s was not found',
                              model.name, str(content['runner_type']))
                continue
            try:
                model = Action.add_or_update(model)
                LOG.audit('Action created. Action %s from %s.', model, action)
            except Exception:
                LOG.exception('Failed to create action %s.', model.name)


def _register_actions_from_packs(base_dir):
    pack_loader = ContentPackLoader()
    dirs = pack_loader.get_content(base_dir=base_dir,
                                   content_type='actions')
    for pack, actions_dir in dirs.items():
        try:
            actions = _get_actions_from_pack(actions_dir)
            _register_actions_from_pack(pack, actions)
        except:
            LOG.exception('Failed registering all actions from pack: %s', actions_dir)


def register_actions():
    return _register_actions_from_packs(cfg.CONF.content.content_pack_path)
