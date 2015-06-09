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

import abc
import importlib

import six

from st2actions import handlers
from st2common import log as logging
from st2common.exceptions.actionrunner import ActionRunnerCreateError
from st2common.util.api import get_full_public_api_url
import st2common.util.action_db as action_utils


__all__ = [
    'ActionRunner',
    'AsyncActionRunner',
    'ShellRunnerMixin'
]


LOG = logging.getLogger(__name__)

# constants to lookup in runner_parameters
RUNNER_COMMAND = 'cmd'


def get_runner(module_name):
    """Load the module and return an instance of the runner."""

    LOG.debug('Runner loading python module: %s', module_name)
    try:
        module = importlib.import_module(module_name, package=None)
    except Exception as e:
        LOG.exception('Failed to import module %s.', module_name)
        raise ActionRunnerCreateError(e)

    LOG.debug('Instance of runner module: %s', module)

    runner = module.get_runner()
    LOG.debug('Instance of runner: %s', runner)
    return runner


@six.add_metaclass(abc.ABCMeta)
class ActionRunner(object):
    """
        The interface that must be implemented by each StackStorm
        Action Runner implementation.
    """

    def __init__(self, runner_id):
        """
        :param id: Runner id.
        :type id: ``str``
        """
        self.runner_id = runner_id

        self.container_service = None
        self.runner_parameters = None
        self.action = None
        self.action_name = None
        self.liveaction = None
        self.liveaction_id = None
        self.entry_point = None
        self.libs_dir_path = None
        self.context = None
        self.callback = None
        self.auth_token = None

    @abc.abstractmethod
    def pre_run(self):
        raise NotImplementedError()

    # Run will need to take an action argument
    # Run may need result data argument
    @abc.abstractmethod
    def run(self, action_parameters):
        raise NotImplementedError()

    def post_run(self, status, result):
        if self.callback and not (set(['url', 'source']) - set(self.callback.keys())):
            handler = handlers.get_handler(self.callback['source'])
            handler.callback(self.callback['url'],
                             self.context,
                             status,
                             result)

    def _get_common_action_env_variables(self):
        """
        Retrieve common ST2_ACTION_ environment variables which will be available to the action.

        Note: Environment variables are prefixed with ST2_ACTION_* so they don't clash with CLI
        environment variables.

        :rtype: ``dict``
        """
        result = {}
        result['ST2_ACTION_API_URL'] = get_full_public_api_url()

        if self.auth_token:
            result['ST2_ACTION_AUTH_TOKEN'] = self.auth_token.token

        return result

    def _log_action_completion(self, logger, result, status, exit_code=None):
        """
        Log action completion event.

        :param result: Action result / output.
        :param status: Action status.
        :param exit_code: Action exit code (optional).
        """
        name = self.action_name
        extra = {
            'result': result,
            'status': status
        }

        if exit_code is not None:
            extra['exit_code'] = exit_code

        logger.debug('Action "%s" completed.' % (name), extra=extra)

    def __str__(self):
        attrs = ', '.join(['%s=%s' % (k, v) for k, v in six.iteritems(self.__dict__)])
        return '%s@%s(%s)' % (self.__class__.__name__, str(id(self)), attrs)


@six.add_metaclass(abc.ABCMeta)
class AsyncActionRunner(ActionRunner):
    pass


class ShellRunnerMixin(object):
    """
    Class which contains utility functions to be used by shell runners.
    """

    def _transform_named_args(self, named_args):
        """
        Transform named arguments to the final form.

        :param named_args: Named arguments.
        :type named_args: ``dict``

        :rtype: ``dict``
        """
        if named_args:
            return {self._kwarg_op + k: v for (k, v) in six.iteritems(named_args)}
        return None

    def _get_script_args(self, action_parameters):
        """
        :param action_parameters: Action parameters.
        :type action_parameters: ``dict``

        :return: (positional_args, named_args)
        :rtype: (``str``, ``dict``)
        """
        # TODO: return list for positional args, command classes should escape it
        # and convert it to string

        is_script_run_as_cmd = self.runner_parameters.get(RUNNER_COMMAND, None)

        pos_args = ''
        named_args = {}

        if is_script_run_as_cmd:
            pos_args = self.runner_parameters.get(RUNNER_COMMAND, '')
            named_args = action_parameters
        else:
            pos_args, named_args = action_utils.get_args(action_parameters, self.action)

        return pos_args, named_args
