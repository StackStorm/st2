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
from st2common.util import loader as action_loader
from st2common.util.config_parser import ContentPackConfigParser
from st2common.constants.action import ACTION_OUTPUT_RESULT_DELIMITER

__all__ = [
    'PythonActionWrapper'
]

LOG = logging.getLogger(__name__)


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

        try:
            config.parse_args(args=self._parent_args)
        except Exception:
            pass

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

        if config:
            LOG.info('Using config "%s" for action "%s"' % (config.file_path,
                                                            self._file_path))

            return action_cls(config=config.config)
        else:
            LOG.info('No config found for action "%s"' % (self._file_path))
            return action_cls(config={})


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
