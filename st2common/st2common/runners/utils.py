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

import os

import logging as stdlib_logging

import six
from oslo_config import cfg

from st2common.constants.action import ACTION_OUTPUT_RESULT_DELIMITER
from st2common import log as logging


__all__ = [
    'PackConfigDict',

    'get_logger_for_python_runner_action',
    'get_action_class_instance',

    'make_read_and_store_stream_func',

    'invoke_post_run',
]

LOG = logging.getLogger(__name__)

# Error which is thrown when Python action tries to access self.config key which doesn't exist
CONFIG_MISSING_ITEM_ERROR = """
Config for pack "%s" is missing key "%s".
Make sure that the config file exists on disk (%s) and contains that key.

Also make sure you run "st2ctl reload --register-configs" when you add a
config and after every change you make to the config.
"""

# Maps logger name to the actual logger instance
# We re-use loggers for the same actions to make sure only a single instance exists for a
# particular action. This way we avoid duplicate log messages, etc.
LOGGERS = {}


class PackConfigDict(dict):
    """
    Dictionary class wraper for pack config dictionaries.

    This class throws a user-friendly exception in case user tries to access config item which
    doesn't exist in the dict.
    """
    def __init__(self, pack_name, *args):
        super(PackConfigDict, self).__init__(*args)
        self._pack_name = pack_name

    def __getitem__(self, key):
        try:
            value = super(PackConfigDict, self).__getitem__(key)
        except KeyError:
            # Note: We use late import to avoid performance overhead
            from oslo_config import cfg

            configs_path = os.path.join(cfg.CONF.system.base_path, 'configs/')
            config_path = os.path.join(configs_path, self._pack_name + '.yaml')
            msg = CONFIG_MISSING_ITEM_ERROR % (self._pack_name, key, config_path)
            raise ValueError(msg)

        return value

    def __setitem__(self, key, value):
        super(PackConfigDict, self).__setitem__(key, value)


def get_logger_for_python_runner_action(action_name, log_level='debug'):
    """
    Set up a logger which logs all the messages with level DEBUG and above to stderr.
    """
    logger_name = 'actions.python.%s' % (action_name)

    if logger_name not in LOGGERS:
        level_name = log_level.upper()
        log_level_constant = getattr(stdlib_logging, level_name, stdlib_logging.DEBUG)
        logger = logging.getLogger(logger_name)

        console = stdlib_logging.StreamHandler()
        console.setLevel(log_level_constant)

        formatter = stdlib_logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
        console.setFormatter(formatter)
        logger.addHandler(console)
        logger.setLevel(log_level_constant)

        LOGGERS[logger_name] = logger
    else:
        logger = LOGGERS[logger_name]

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


def make_read_and_store_stream_func(execution_db, action_db, store_data_func):
    """
    Factory function which returns a function for reading from a stream (stdout / stderr).

    This function writes read data into a buffer and stores it in a database.
    """
    # NOTE: This import has intentionally been moved here to avoid massive performance overhead
    # (1+ second) for other functions inside this module which don't need to use those imports.
    import eventlet

    def read_and_store_stream(stream, buff):
        try:
            while not stream.closed:
                line = stream.readline()
                if not line:
                    break

                if isinstance(line, six.binary_type):
                    line = line.decode('utf-8')

                buff.write(line)

                # Filter out result delimiter lines
                if ACTION_OUTPUT_RESULT_DELIMITER in line:
                    continue

                if cfg.CONF.actionrunner.stream_output:
                    store_data_func(execution_db=execution_db, action_db=action_db, data=line)
        except RuntimeError:
            # process was terminated abruptly
            pass
        except eventlet.support.greenlets.GreenletExit:
            # Green thread exited / was killed
            pass

    return read_and_store_stream


def invoke_post_run(liveaction_db, action_db=None):
    # NOTE: This import has intentionally been moved here to avoid massive performance overhead
    # (1+ second) for other functions inside this module which don't need to use those imports.
    from st2common.runners import base as runners
    from st2common.util import action_db as action_db_utils
    from st2common.content import utils as content_utils

    LOG.info('Invoking post run for action execution %s.', liveaction_db.id)

    # Identify action and runner.
    if not action_db:
        action_db = action_db_utils.get_action_by_ref(liveaction_db.action)

    if not action_db:
        LOG.error('Unable to invoke post run. Action %s no longer exists.', liveaction_db.action)
        return

    LOG.info('Action execution %s runs %s of runner type %s.',
             liveaction_db.id, action_db.name, action_db.runner_type['name'])

    # Get instance of the action runner and related configuration.
    runner_type_db = action_db_utils.get_runnertype_by_name(action_db.runner_type['name'])

    runner = runners.get_runner(
        package_name=runner_type_db.runner_package,
        module_name=runner_type_db.runner_module)

    entry_point = content_utils.get_entry_point_abs_path(
        pack=action_db.pack,
        entry_point=action_db.entry_point)

    libs_dir_path = content_utils.get_action_libs_abs_path(
        pack=action_db.pack,
        entry_point=action_db.entry_point)

    # Configure the action runner.
    runner.runner_type_db = runner_type_db
    runner.action = action_db
    runner.action_name = action_db.name
    runner.liveaction = liveaction_db
    runner.liveaction_id = str(liveaction_db.id)
    runner.entry_point = entry_point
    runner.context = getattr(liveaction_db, 'context', dict())
    runner.callback = getattr(liveaction_db, 'callback', dict())
    runner.libs_dir_path = libs_dir_path

    # Invoke the post_run method.
    runner.post_run(liveaction_db.status, liveaction_db.result)
