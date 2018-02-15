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

from __future__ import absolute_import
import abc

import six
import yaml
from oslo_config import cfg

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.constants import pack as pack_constants
from st2common.exceptions.actionrunner import ActionRunnerCreateError
from st2common.util import action_db as action_utils
from st2common.util.loader import register_runner
from st2common.util.loader import register_callback_module
from st2common.util.api import get_full_public_api_url
from st2common.util.deprecation import deprecated

__all__ = [
    'ActionRunner',
    'AsyncActionRunner',
    'PollingAsyncActionRunner',
    'ShellRunnerMixin',

    'get_runner',
    'get_metadata'
]


LOG = logging.getLogger(__name__)

# constants to lookup in runner_parameters
RUNNER_COMMAND = 'cmd'


def get_runner(package_name, module_name, config=None):
    """
    Load the module and return an instance of the runner.
    """

    if not package_name:
        # Backward compatibility for Pre 2.7.0 where package name always equaled module name
        package_name = module_name

    LOG.debug('Runner loading Python module: %s.%s', package_name, module_name)

    try:
        # TODO: Explore modifying this to support register_plugin
        module = register_runner(package_name=package_name, module_name=module_name)
    except Exception as e:
        msg = ('Failed to import runner module %s.%s' % (package_name, module_name))
        LOG.exception(msg)

        raise ActionRunnerCreateError('%s\n\n%s' % (msg, str(e)))

    LOG.debug('Instance of runner module: %s', module)

    if config:
        runner_kwargs = {'config': config}
    else:
        runner_kwargs = {}

    runner = module.get_runner(**runner_kwargs)
    LOG.debug('Instance of runner: %s', runner)
    return runner


def get_metadata(package_name):
    """
    Return runner related metadata for the provided runner package name.

    :rtype: ``list`` of ``dict``
    """
    import pkg_resources

    file_path = pkg_resources.resource_filename(package_name, 'runner.yaml')

    with open(file_path, 'r') as fp:
        content = fp.read()

    metadata = yaml.safe_load(content)
    return metadata


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

    def pause(self):
        runner_name = getattr(self.runner_type_db, 'name', 'unknown')
        raise NotImplementedError('Pause is not supported for runner %s.' % runner_name)

    def resume(self):
        runner_name = getattr(self.runner_type_db, 'name', 'unknown')
        raise NotImplementedError('Resume is not supported for runner %s.' % runner_name)

    def cancel(self):
        return (
            action_constants.LIVEACTION_STATUS_CANCELED,
            self.liveaction.result,
            self.liveaction.context
        )

    def post_run(self, status, result):
        callback = self.callback or {}

        if callback and not (set(['url', 'source']) - set(callback.keys())):
            callback_url = callback['url']
            callback_module_name = callback['source']

            try:
                callback_module = register_callback_module(callback_module_name)
            except:
                LOG.exception('Failed importing callback module: %s', callback_module_name)

            callback_handler = callback_module.get_instance()

            callback_handler.callback(
                callback_url,
                self.context,
                status,
                result
            )

    @deprecated
    def get_pack_name(self):
        return self.get_pack_ref()

    def get_pack_ref(self):
        """
        Retrieve pack name for the action which is being currently executed.

        :rtype: ``str``
        """
        if self.action:
            return self.action.pack

        return pack_constants.DEFAULT_PACK_NAME

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
        result['ST2_ACTION_PACK_NAME'] = self.get_pack_ref()
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


@six.add_metaclass(abc.ABCMeta)
class PollingAsyncActionRunner(AsyncActionRunner):
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
