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

import sys
import json
import argparse
from oslo_config import cfg

from st2common import log as logging
from st2actions import config
from st2actions.runners.pythonrunner import Action
from st2actions.runners.utils import get_logger_for_python_runner_action
from st2actions.runners.utils import get_action_class_instance
from st2common.util import loader as action_loader
from st2common.util.config_loader import ContentPackConfigLoader
from st2common.constants.action import ACTION_OUTPUT_RESULT_DELIMITER
from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.constants.runners import PYTHON_RUNNER_INVALID_ACTION_STATUS_EXIT_CODE
from st2common.service_setup import db_setup
from st2common.services.datastore import DatastoreService

__all__ = [
    'PythonActionWrapper',
    'ActionService'
]

LOG = logging.getLogger(__name__)

INVALID_STATUS_ERROR_MESSAGE = """
If this is an existing action which returns a tuple with two items, it needs to be updated to
either:

1. Return a list instead of a tuple
2. Return a tuple where a first items is a status flag - (True, ('item1', 'item2'))

For more information, please see: https://docs.stackstorm.com/upgrade_notes.html#st2-v1-6
""".strip()


class ActionService(object):
    """
    Instance of this class is passed to the action instance and exposes "public"
    methods which can be called by the action.
    """

    def __init__(self, action_wrapper):
        logger = get_logger_for_python_runner_action(action_name=action_wrapper._class_name)

        self._action_wrapper = action_wrapper
        self._datastore_service = DatastoreService(logger=logger,
                                                   pack_name=self._action_wrapper._pack,
                                                   class_name=self._action_wrapper._class_name,
                                                   api_username='action_service')

    ##################################
    # Methods for datastore management
    ##################################

    def list_values(self, local=True, prefix=None):
        return self._datastore_service.list_values(local, prefix)

    def get_value(self, name, local=True, scope=SYSTEM_SCOPE, decrypt=False):
        return self._datastore_service.get_value(name, local, scope=scope, decrypt=decrypt)

    def set_value(self, name, value, ttl=None, local=True, scope=SYSTEM_SCOPE, encrypt=False):
        return self._datastore_service.set_value(name, value, ttl, local, scope=scope,
                                                 encrypt=encrypt)

    def delete_value(self, name, local=True, scope=SYSTEM_SCOPE):
        return self._datastore_service.delete_value(name, local)


class PythonActionWrapper(object):
    def __init__(self, pack, file_path, parameters=None, user=None, parent_args=None):
        """
        :param pack: Name of the pack this action belongs to.
        :type pack: ``str``

        :param file_path: Path to the action module.
        :type file_path: ``str``

        :param parameters: action parameters.
        :type parameters: ``dict`` or ``None``

        :param user: Name of the user who triggered this action execution.
        :type user: ``str``

        :param parent_args: Command line arguments passed to the parent process.
        :type parse_args: ``list``
        """

        self._pack = pack
        self._file_path = file_path
        self._parameters = parameters or {}
        self._user = user
        self._parent_args = parent_args or []
        self._class_name = None
        self._logger = logging.getLogger('PythonActionWrapper')

        try:
            config.parse_args(args=self._parent_args)
        except Exception:
            pass

        db_setup()

        # Note: We can only set a default user value if one is not provided after parsing the
        # config
        if not self._user:
            self._user = cfg.CONF.system_user.user

    def run(self):
        action = self._get_action_instance()
        output = action.run(**self._parameters)

        if isinstance(output, tuple) and len(output) == 2:
            # run() method returned status and data - (status, data)
            action_status = output[0]
            action_result = output[1]
        else:
            # run() method returned only data, no status (pre StackStorm v1.6)
            action_status = None
            action_result = output

        action_output = {
            'result': action_result,
            'status': None
        }

        if action_status is not None and not isinstance(action_status, bool):
            sys.stderr.write('Status returned from the action run() method must either be '
                             'True or False, got: %s\n' % (action_status))
            sys.stderr.write(INVALID_STATUS_ERROR_MESSAGE)
            sys.exit(PYTHON_RUNNER_INVALID_ACTION_STATUS_EXIT_CODE)

        if action_status is not None and isinstance(action_status, bool):
            action_output['status'] = action_status

        try:
            print_output = json.dumps(action_output)
        except Exception:
            print_output = str(action_output)

        # Print output to stdout so the parent can capture it
        sys.stdout.write(ACTION_OUTPUT_RESULT_DELIMITER)
        sys.stdout.write(print_output + '\n')
        sys.stdout.write(ACTION_OUTPUT_RESULT_DELIMITER)

    def _get_action_instance(self):
        actions_cls = action_loader.register_plugin(Action, self._file_path)
        action_cls = actions_cls[0] if actions_cls and len(actions_cls) > 0 else None

        if not action_cls:
            raise Exception('File "%s" has no action or the file doesn\'t exist.' %
                            (self._file_path))

        config_loader = ContentPackConfigLoader(pack_name=self._pack, user=self._user)
        config = config_loader.get_config()

        if config:
            LOG.info('Found config for action "%s"' % (self._file_path))
        else:
            LOG.info('No config found for action "%s"' % (self._file_path))
            config = None

        action_service = ActionService(action_wrapper=self)
        action_instance = get_action_class_instance(action_cls=action_cls,
                                                    config=config,
                                                    action_service=action_service)
        return action_instance


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Python action runner process wrapper')
    parser.add_argument('--pack', required=True,
                        help='Name of the pack this action belongs to')
    parser.add_argument('--file-path', required=True,
                        help='Path to the action module')
    parser.add_argument('--parameters', required=False,
                        help='Serialized action parameters')
    parser.add_argument('--user', required=False,
                        help='User who triggered the action execution')
    parser.add_argument('--parent-args', required=False,
                        help='Command line arguments passed to the parent process')
    args = parser.parse_args()

    parameters = args.parameters
    parameters = json.loads(parameters) if parameters else {}
    user = args.user
    parent_args = json.loads(args.parent_args) if args.parent_args else []

    assert isinstance(parent_args, list)
    obj = PythonActionWrapper(pack=args.pack,
                              file_path=args.file_path,
                              parameters=parameters,
                              user=user,
                              parent_args=parent_args)

    obj.run()
