# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import os
import abc
import shutil
import tempfile
from subprocess import list2cmdline

import six
import yaml
from oslo_config import cfg

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.constants import pack as pack_constants
from st2common.constants.runners import RUNNERS_NAMESPACE, MANIFEST_FILE_NAME
from st2common.content.utils import get_pack_directory
from st2common.content.utils import get_pack_base_path
from st2common.exceptions import actionrunner as exc
from st2common.util.loader import get_plugin_instance
from st2common.util.loader import get_available_plugins
from st2common.util.api import get_full_public_api_url
from st2common.util.deprecation import deprecated
from st2common.util.green.shell import run_command
from st2common.util import concurrency

subprocess = concurrency.get_subprocess_module()

__all__ = [
    "ActionRunner",
    "AsyncActionRunner",
    "PollingAsyncActionRunner",
    "GitWorktreeActionRunner",
    "PollingAsyncActionRunner",
    "ShellRunnerMixin",
    "get_runner_module",
    "get_runner",
    "get_metadata",
]


LOG = logging.getLogger(__name__)

# constants to lookup in runner_parameters
RUNNER_COMMAND = "cmd"
RUNNER_CONTENT_VERSION = "content_version"
RUNNER_DEBUG = "debug"


def get_runner(name, config=None):
    """
    Load the module and return an instance of the runner.
    """
    LOG.debug("Runner loading Python module: %s", name)

    module = get_runner_module(name=name)

    LOG.debug("Instance of runner module: %s", module)

    if config:
        runner_kwargs = {"config": config}
    else:
        runner_kwargs = {}

    runner = module.get_runner(**runner_kwargs)
    LOG.debug("Instance of runner: %s", runner)
    return runner


def get_runner_module(name):
    """
    Load runner driver and return reference to the runner driver module.
    """

    # NOTE: For backward compatibility we also support "_" in place of "-"
    from stevedore.exception import NoMatches

    try:
        module = get_plugin_instance(RUNNERS_NAMESPACE, name, invoke_on_load=False)
    except NoMatches:
        name = name.replace("_", "-")

        try:
            module = get_plugin_instance(RUNNERS_NAMESPACE, name, invoke_on_load=False)
        except Exception as e:
            available_runners = get_available_plugins(namespace=RUNNERS_NAMESPACE)
            available_runners = ", ".join(available_runners)
            msg = (
                "Failed to find runner %s. Make sure that the runner is available and installed "
                "in StackStorm virtual environment. Available runners are: %s"
                % (name, available_runners)
            )
            LOG.exception(msg)

            raise exc.ActionRunnerCreateError("%s\n\n%s" % (msg, six.text_type(e)))

    return module


def get_metadata(package_name):
    """
    Return runner related metadata for the provided runner package name.

    :rtype: ``list`` of ``dict``
    """
    import pkg_resources

    file_path = pkg_resources.resource_filename(package_name, MANIFEST_FILE_NAME)

    with open(file_path, "r") as fp:
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
        self.runner_type = None
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
        self.auth_token = None
        self.rerun_ex_ref = None
        self._debug = None

    def pre_run(self):
        # Handle runner "enabled" attribute
        runner_enabled = getattr(self.runner_type, "enabled", True)
        runner_name = getattr(self.runner_type, "name", "unknown")

        if not runner_enabled:
            msg = 'Runner "%s" has been disabled by the administrator.' % runner_name
            raise ValueError(msg)

        runner_parameters = getattr(self, "runner_parameters", {}) or {}
        self._debug = runner_parameters.get(RUNNER_DEBUG, False)

    # Run will need to take an action argument
    # Run may need result data argument
    @abc.abstractmethod
    def run(self, action_parameters):
        raise NotImplementedError()

    def pause(self):
        runner_name = getattr(self.runner_type, "name", "unknown")
        raise NotImplementedError("Pause is not supported for runner %s." % runner_name)

    def resume(self):
        runner_name = getattr(self.runner_type, "name", "unknown")
        raise NotImplementedError(
            "Resume is not supported for runner %s." % runner_name
        )

    def cancel(self):
        return (
            action_constants.LIVEACTION_STATUS_CANCELED,
            self.liveaction.result,
            self.liveaction.context,
        )

    def post_run(self, status, result):
        pass

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
        context = getattr(self, "context", {}) or {}
        user = context.get("user", cfg.CONF.system_user.user)

        return user

    def _get_common_action_env_variables(self):
        """
        Retrieve common ST2_ACTION_ environment variables which will be available to the action.

        Note: Environment variables are prefixed with ST2_ACTION_* so they don't clash with CLI
        environment variables.

        :rtype: ``dict``
        """
        result = {}
        result["ST2_ACTION_PACK_NAME"] = self.get_pack_ref()
        result["ST2_ACTION_EXECUTION_ID"] = str(self.execution_id)
        result["ST2_ACTION_API_URL"] = get_full_public_api_url()
        result["ST2_ACTION_DEBUG"] = str(self._debug)

        if self.auth_token:
            result["ST2_ACTION_AUTH_TOKEN"] = self.auth_token.token

        return result

    def __str__(self):
        attrs = ", ".join(["%s=%s" % (k, v) for k, v in six.iteritems(self.__dict__)])
        return "%s@%s(%s)" % (self.__class__.__name__, str(id(self)), attrs)


@six.add_metaclass(abc.ABCMeta)
class AsyncActionRunner(ActionRunner):
    pass


class PollingAsyncActionRunner(AsyncActionRunner):
    @classmethod
    def is_polling_enabled(cls):
        return True


@six.add_metaclass(abc.ABCMeta)
class GitWorktreeActionRunner(ActionRunner):
    """
    Base class for runners which work with files (e.g. Python runner, Local script runner)
    and support git worktree functionality - ability to use a file under a specific git revision
    from a git repository.

    This revision is specified using "content_version" runner parameter.
    """

    WORKTREE_DIRECTORY_PREFIX = "st2-git-worktree-"

    def __init__(self, runner_id):
        super(GitWorktreeActionRunner, self).__init__(runner_id=runner_id)

        # Git work tree related attributes
        self.git_worktree_path = None
        self.git_worktree_revision = None

    def pre_run(self):
        super(GitWorktreeActionRunner, self).pre_run()

        # Handle git worktree creation
        self._content_version = self.runner_parameters.get(RUNNER_CONTENT_VERSION, None)

        if self._content_version:
            self.create_git_worktree(content_version=self._content_version)

            # Override entry_point so it points to git worktree directory
            pack_name = self.get_pack_name()
            entry_point = self._get_entry_point_for_worktree_path(
                pack_name=pack_name,
                entry_point=self.entry_point,
                worktree_path=self.git_worktree_path,
            )

            if not entry_point.startswith(self.git_worktree_path):
                raise ValueError(
                    f"The entry point value {self.entry_point}"
                    " does not start with the git worktree path"
                    f"{self.git_worktree_path}."
                )

            self.entry_point = entry_point

    def post_run(self, status, result):
        super(GitWorktreeActionRunner, self).post_run(status=status, result=result)

        # Remove git worktree directories (if used and available)
        if self.git_worktree_path and self.git_worktree_revision:
            pack_name = self.get_pack_name()
            self.cleanup_git_worktree(
                worktree_path=self.git_worktree_path,
                content_version=self.git_worktree_revision,
                pack_name=pack_name,
            )

    def create_git_worktree(self, content_version):
        """
        Create a git worktree for the provided git content version.

        :return: Path to the created git worktree directory.
        :rtype: ``str``
        """
        pack_name = self.get_pack_name()
        pack_directory = get_pack_directory(pack_name=pack_name)
        worktree_path = tempfile.mkdtemp(prefix=self.WORKTREE_DIRECTORY_PREFIX)

        # Set class variables
        self.git_worktree_revision = content_version
        self.git_worktree_path = worktree_path

        extra = {
            "pack_name": pack_name,
            "pack_directory": pack_directory,
            "content_version": content_version,
            "worktree_path": worktree_path,
        }

        if not os.path.isdir(pack_directory):
            msg = (
                'Failed to create git worktree for pack "%s". Pack directory "%s" doesn\'t '
                "exist." % (pack_name, pack_directory)
            )
            raise ValueError(msg)

        args = [
            "git",
            "-C",
            pack_directory,
            "worktree",
            "add",
            worktree_path,
            content_version,
        ]
        cmd = list2cmdline(args)

        LOG.debug(
            'Creating git worktree for pack "%s", content version "%s" and execution '
            'id "%s" in "%s"'
            % (pack_name, content_version, self.execution_id, worktree_path),
            extra=extra,
        )
        LOG.debug("Command: %s" % (cmd))
        exit_code, stdout, stderr, timed_out = run_command(
            cmd=cmd,
            cwd=pack_directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )

        if exit_code != 0:
            self._handle_git_worktree_error(
                pack_name=pack_name,
                pack_directory=pack_directory,
                content_version=content_version,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
            )
        else:
            LOG.debug('Git worktree created in "%s"' % (worktree_path), extra=extra)

        # Make sure system / action runner user can access that directory
        args = ["chmod", "777", worktree_path]
        cmd = list2cmdline(args)
        run_command(cmd=cmd, shell=True)

        return worktree_path

    def cleanup_git_worktree(self, worktree_path, pack_name, content_version):
        """
        Remove / cleanup the provided git worktree directory.

        :rtype: ``bool``
        """
        # Safety check to make sure we don't remove something outside /tmp
        if not worktree_path.startswith("/tmp"):
            raise ValueError(
                f"The worktree path is not within /tmp (was {type(worktree_path)})."
            )
        if not worktree_path.startswith("/tmp/%s" % (self.WORKTREE_DIRECTORY_PREFIX)):
            raise ValueError(
                f"The worktree path is not within /tmp/ (was {type(worktree_path)})."
            )

        if self._debug:
            LOG.debug(
                'Not removing git worktree "%s" because debug mode is enabled'
                % (worktree_path)
            )
        else:
            LOG.debug(
                'Removing git worktree "%s" for pack "%s" and content version "%s"'
                % (worktree_path, pack_name, content_version)
            )

            try:
                shutil.rmtree(worktree_path, ignore_errors=True)
            except Exception:
                msg = "Unable to remove / cleanup the provided git worktree directory."
                LOG.exception(msg)

        return True

    def _handle_git_worktree_error(
        self, pack_name, pack_directory, content_version, exit_code, stdout, stderr
    ):
        """
        Handle "git worktree" related errors and throw a more user-friendly exception.
        """
        error_prefix = 'Failed to create git worktree for pack "%s": ' % (pack_name)

        if isinstance(stdout, six.binary_type):
            stdout = stdout.decode("utf-8")

        if isinstance(stderr, six.binary_type):
            stderr = stderr.decode("utf-8")

        # 1. Installed version of git which doesn't support worktree command
        if "git: 'worktree' is not a git command." in stderr:
            msg = (
                "Installed git version doesn't support git worktree command. "
                "To be able to utilize this functionality you need to use git "
                ">= 2.5.0."
            )
            raise ValueError(error_prefix + msg)

        # 2. Provided pack directory is not a git repository
        if "Not a git repository" in stderr:
            msg = (
                'Pack directory "%s" is not a git repository. To utilize this functionality, '
                "pack directory needs to be a git repository." % (pack_directory)
            )
            raise ValueError(error_prefix + msg)

        # 3. Invalid revision provided
        if "invalid reference" in stderr:
            msg = (
                'Invalid content_version "%s" provided. Make sure that git repository is up '
                "to date and contains that revision." % (content_version)
            )
            raise ValueError(error_prefix + msg)

    def _get_entry_point_for_worktree_path(self, pack_name, entry_point, worktree_path):
        """
        Method which returns path to an action entry point which is located inside the git
        worktree directory.

        :rtype: ``str``
        """
        pack_base_path = get_pack_base_path(pack_name=pack_name)

        new_entry_point = entry_point.replace(pack_base_path, "")

        # Remove leading slash (if any)
        if new_entry_point.startswith("/"):
            new_entry_point = new_entry_point[1:]

        new_entry_point = os.path.join(worktree_path, new_entry_point)

        # Check to prevent directory traversal
        common_prefix = os.path.commonprefix([worktree_path, new_entry_point])
        if common_prefix != worktree_path:
            raise ValueError("entry_point is not located inside the pack directory")

        return new_entry_point


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
        # Lazy import to speed up import of this module
        from st2common.util import action_db as action_utils

        # TODO: return list for positional args, command classes should escape it
        # and convert it to string

        is_script_run_as_cmd = self.runner_parameters.get(RUNNER_COMMAND, None)

        pos_args = ""
        named_args = {}

        if is_script_run_as_cmd:
            pos_args = self.runner_parameters.get(RUNNER_COMMAND, "")
            named_args = action_parameters
        else:
            pos_args, named_args = action_utils.get_args(action_parameters, self.action)

        return pos_args, named_args
