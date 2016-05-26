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
from oslo_config import cfg

from st2actions import handlers
from st2common import log as logging
from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.exceptions.actionrunner import ActionRunnerCreateError
from st2common.util import action_db as action_utils
from st2common.util.api import get_full_public_api_url


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

        self.runner_type_db = None
        self.container_service = None
        self.runner_parameters = None
        self.action = None
        self.action_name = None
        self.liveaction = None
        self.liveaction_id = None
        self.execution = None
        self.execution_id = None
        self.entry_point = None
        self.libs_dir_path = None
        self.context = None
        self.callback = None
        self.auth_token = None
        self.rerun_ex_ref = None

    def pre_run(self):
        runner_enabled = getattr(self.runner_type_db, 'enabled', True)
        runner_name = getattr(self.runner_type_db, 'name', 'unknown')
        if not runner_enabled:
            msg = ('Runner "%s" has been disabled by the administrator' %
                   (runner_name))
            raise ValueError(msg)

    # Run will need to take an action argument
    # Run may need result data argument
    @abc.abstractmethod
    def run(self, action_parameters):
        raise NotImplementedError()

    def cancel(self):
        pass

    def post_run(self, status, result):
        callback = self.callback or {}
        if callback and not (set(['url', 'source']) - set(callback.keys())):
            handler = handlers.get_handler(callback['source'])
            handler.callback(callback['url'],
                             self.context,
                             status,
                             result)

    def get_pack_name(self):
        """
        Retrieve pack name for the action which is being currently executed.

        :rtype: ``str``
        """
        if self.action:
            return self.action.pack

        return DEFAULT_PACK_NAME

    def get_user(self):
        """
        Retrieve a name of the user which triggered this action execution.

        :rtype: ``str``
        """
        context = getattr(self, 'context', {}) or {}
        user = context.get('user', cfg.CONF.system_user.user)

        return user

    def _get_common_action_env_variables(self):
        """
        Retrieve common ST2_ACTION_ environment variables which will be available to the action.

        Note: Environment variables are prefixed with ST2_ACTION_* so they don't clash with CLI
        environment variables.

        :rtype: ``dict``
        """
        result = {}
        result['ST2_ACTION_PACK_NAME'] = self.get_pack_name()
        result['ST2_ACTION_EXECUTION_ID'] = str(self.execution_id)
        result['ST2_ACTION_API_URL'] = get_full_public_api_url()

        if self.auth_token:
            result['ST2_ACTION_AUTH_TOKEN'] = self.auth_token.token

        return result

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
