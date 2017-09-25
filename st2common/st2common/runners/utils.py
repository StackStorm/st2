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

import logging as stdlib_logging

from st2actions.container.service import RunnerContainerService
from st2common import log as logging
from st2common.runners import base as runners
from st2common.util import action_db as action_db_utils


__all__ = [
    'get_logger_for_python_runner_action',
    'get_action_class_instance'
]

LOG = logging.getLogger(__name__)


def get_logger_for_python_runner_action(action_name):
    """
    Set up a logger which logs all the messages with level DEBUG and above to stderr.
    """
    logger_name = 'actions.python.%s' % (action_name)
    logger = logging.getLogger(logger_name)

    console = stdlib_logging.StreamHandler()
    console.setLevel(stdlib_logging.DEBUG)

    formatter = stdlib_logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    logger.setLevel(stdlib_logging.DEBUG)

    return logger


def get_action_class_instance(action_cls, config=None, action_service=None):
    """
    Instantiate and return Action class instance.

    :param action_cls: Action class to instantiate.
    :type action_cls: ``class``

    :param config: Config to pass to the action class.
    :type config: ``dict``

    :param action_service: ActionService instance to pass to the class.
    :type action_service: :class:`ActionService`
    """
    kwargs = {}
    kwargs['config'] = config
    kwargs['action_service'] = action_service

    # Note: This is done for backward compatibility reasons. We first try to pass
    # "action_service" argument to the action class constructor, but if that doesn't work (e.g. old
    # action which hasn't been updated yet), we resort to late assignment post class instantiation.
    # TODO: Remove in next major version once all the affected actions have been updated.
    try:
        action_instance = action_cls(**kwargs)
    except TypeError as e:
        if 'unexpected keyword argument \'action_service\'' not in str(e):
            raise e

        LOG.debug('Action class (%s) constructor doesn\'t take "action_service" argument, '
                  'falling back to late assignment...' % (action_cls.__class__.__name__))

        action_service = kwargs.pop('action_service', None)
        action_instance = action_cls(**kwargs)
        action_instance.action_service = action_service

    return action_instance


def invoke_post_run(liveaction_db, action_db=None):
    LOG.info('Invoking post run for action execution %s.', liveaction_db.id)

    # Identify action and runner.
    if not action_db:
        action_db = action_db_utils.get_action_by_ref(liveaction_db.action)

    if not action_db:
        LOG.exception('Unable to invoke post run. Action %s no longer exists.',
                      liveaction_db.action)
        return

    LOG.info('Action execution %s runs %s of runner type %s.',
             liveaction_db.id, action_db.name, action_db.runner_type['name'])

    # Get an instance of the action runner.
    runnertype_db = action_db_utils.get_runnertype_by_name(action_db.runner_type['name'])
    runner = runners.get_runner(runnertype_db.runner_module)

    # Configure the action runner.
    runner.container_service = RunnerContainerService()
    runner.action = action_db
    runner.action_name = action_db.name
    runner.action_execution_id = str(liveaction_db.id)
    runner.entry_point = RunnerContainerService.get_entry_point_abs_path(
        pack=action_db.pack, entry_point=action_db.entry_point)
    runner.context = getattr(liveaction_db, 'context', dict())
    runner.callback = getattr(liveaction_db, 'callback', dict())
    runner.libs_dir_path = RunnerContainerService.get_action_libs_abs_path(
        pack=action_db.pack, entry_point=action_db.entry_point)

    # Invoke the post_run method.
    runner.post_run(liveaction_db.status, liveaction_db.result)
