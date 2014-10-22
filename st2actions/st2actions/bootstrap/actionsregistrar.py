import glob
import json
import os

from oslo.config import cfg
import six

from st2common import log as logging
from st2common.content.loader import ContentPackLoader
from st2common.content.validators import RequirementsValidator
from st2common.persistence.action import Action
from st2common.models.db.action import ActionDB
from st2common.util.action_db import get_runnertype_by_name

LOG = logging.getLogger(__name__)


class ActionsRegistrar(object):
    def _get_actions_from_pack(self, pack):
        actions = glob.glob(pack + '/*.json')
        # Exclude global actions configuration file
        actions = [file_path for file_path in actions if
                   'actions/config.json' not in file_path]
        return actions

    def _register_action(self, pack, action):
        with open(action, 'r') as fd:
            try:
                content = json.load(fd)
            except ValueError:
                LOG.exception('Failed loading action json from %s.', action)
                raise

            try:
                model = Action.get_by_name(str(content['name']))
            except ValueError:
                model = ActionDB()
            model.name = content['name']
            model.description = content['description']
            model.enabled = content['enabled']
            model.pack = pack
            model.entry_point = content['entry_point']
            model.parameters = content.get('parameters', {})
            model.required_parameters = content.get('required_parameters', [])
            runner_type = str(content['runner_type'])
            valid_runner_type, runner_type_db = self._has_valid_runner_type(runner_type)
            if valid_runner_type:
                model.runner_type = {'name': runner_type_db.name}
            else:
                LOG.exception('Runner type %s doesn\'t exist.')
                raise

            try:
                model = Action.add_or_update(model)
                LOG.audit('Action created. Action %s from %s.', model, action)
            except Exception:
                LOG.exception('Failed to write action to db %s.', model.name)
                raise

    def _has_valid_runner_type(self, runner_type):
        try:
            return True, get_runnertype_by_name(runner_type)
        except:
            return False, None

    def _register_actions_from_pack(self, pack, actions):
        for action in actions:
            try:
                LOG.debug('Loading action from %s.', action)
                self._register_action(pack, action)
            except Exception:
                LOG.exception('Unable to register action: %s', action)
                continue

    # XXX: Requirements for actions is tricky because actions can execute remotely.
    # Currently, this method is unused.
    def _is_requirements_ok(self, actions_dir):
        rqmnts_file = os.path.join(actions_dir, 'requirements.txt')

        if not os.path.exists(rqmnts_file):
            return True

        missing = RequirementsValidator.validate(rqmnts_file)
        if missing:
            LOG.warning('Actions in %s missing dependencies: %s', actions_dir, ','.join(missing))
            return False
        return True

    def register_actions_from_packs(self, base_dir):
        pack_loader = ContentPackLoader()
        dirs = pack_loader.get_content(base_dir=base_dir,
                                       content_type='actions')
        for pack, actions_dir in six.iteritems(dirs):
            try:
                actions = self._get_actions_from_pack(actions_dir)
                self._register_actions_from_pack(pack, actions)
            except:
                LOG.exception('Failed registering all actions from pack: %s', actions_dir)


def register_actions(packs_base_path=None):
    if not packs_base_path:
        packs_base_path = cfg.CONF.content.packs_base_path
    return ActionsRegistrar().register_actions_from_packs(packs_base_path)
