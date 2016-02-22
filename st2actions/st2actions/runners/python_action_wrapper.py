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

from st2common import log as logging
from st2actions import config
from st2actions.runners.pythonrunner import Action
from st2actions.runners.utils import get_logger_for_python_runner_action
from st2actions.runners.utils import get_action_class_instance
from st2common.util import loader as action_loader
from st2common.util.config_parser import ContentPackConfigParser
from st2common.constants.action import ACTION_OUTPUT_RESULT_DELIMITER
from st2common.service_setup import db_setup
from st2common.services.datastore import DatastoreService

__all__ = [
    'PythonActionWrapper'
]

LOG = logging.getLogger(__name__)


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

    def get_value(self, name, local=True):
        return self._datastore_service.get_value(name, local)

    def set_value(self, name, value, ttl=None, local=True):
        return self._datastore_service.set_value(name, value, ttl, local)

    def delete_value(self, name, local=True):
        return self._datastore_service.delete_value(name, local)


class PythonActionWrapper(object):
    def __init__(self, pack, file_path, parameters=None, parent_args=None):
        """
        :param pack: Name of the pack this action belongs to.
        :type pack: ``str``

        :param file_path: Path to the action module.
        :type file_path: ``str``

        :param parameters: action parameters.
        :type parameters: ``dict`` or ``None``

        :param parent_args: Command line arguments passed to the parent process.
        :type parse_args: ``list``
        """

        self._pack = pack
        self._file_path = file_path
        self._parameters = parameters or {}
        self._parent_args = parent_args or []
        self._class_name = None
        self._logger = logging.getLogger('PythonActionWrapper')

        try:
            config.parse_args(args=self._parent_args)
        except Exception:
            pass
        else:
            db_setup()

    def run(self):
        action = self._get_action_instance()
        output = action.run(**self._parameters)

        # Print output to stdout so the parent can capture it
        sys.stdout.write(ACTION_OUTPUT_RESULT_DELIMITER)
        print_output = None
        try:
            print_output = json.dumps(output)
        except:
            print_output = str(output)
        sys.stdout.write(print_output + '\n')
        sys.stdout.write(ACTION_OUTPUT_RESULT_DELIMITER)

    def _get_action_instance(self):
        actions_cls = action_loader.register_plugin(Action, self._file_path)
        action_cls = actions_cls[0] if actions_cls and len(actions_cls) > 0 else None

        if not action_cls:
            raise Exception('File "%s" has no action or the file doesn\'t exist.' %
                            (self._file_path))

        config_parser = ContentPackConfigParser(pack_name=self._pack)
        config = config_parser.get_action_config(action_file_path=self._file_path)

        kwargs = {}
        if config:
            LOG.info('Using config "%s" for action "%s"' % (config.file_path,
                                                            self._file_path))
            kwargs['config'] = config.config
        else:
            LOG.info('No config found for action "%s"' % (self._file_path))
            kwargs['config'] = {}

        action_service = ActionService(action_wrapper=self)
        kwargs['action_service'] = action_service

        action_instance = get_action_class_instance(action_cls=action_cls,
                                                    kwargs=kwargs)
        return action_instance


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Python action runner process wrapper')
    parser.add_argument('--pack', required=True,
                        help='Name of the pack this action belongs to')
    parser.add_argument('--file-path', required=True,
                        help='Path to the action module')
    parser.add_argument('--parameters', required=False,
                        help='Serialized action parameters')
    parser.add_argument('--parent-args', required=False,
                        help='Command line arguments passed to the parent process')
    args = parser.parse_args()

    parameters = args.parameters
    parameters = json.loads(parameters) if parameters else {}
    parent_args = json.loads(args.parent_args) if args.parent_args else []

    assert isinstance(parent_args, list)

    obj = PythonActionWrapper(pack=args.pack,
                              file_path=args.file_path,
                              parameters=parameters,
                              parent_args=parent_args)

    obj.run()
