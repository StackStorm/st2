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

import copy

import logging as stdlib_logging

from st2common import log as logging

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


def get_action_class_instance(action_cls, kwargs):
    """
    Instantiate and return Action class instance.
    """
    # Note: This is done for backward compatibility reasons. We first try to pass
    # "action_service" argument to the action class constructor, but if that doesn't work
    # (e.g. old action which hasn't been updated yet), we resort to late assignment.
    try:
        action_instance = action_cls(**kwargs)
    except TypeError as e:
        if 'unexpected keyword argument \'action_service\'' not in str(e):
            raise e

        LOG.debug('Action class constructor doesn\'t take "action_service" argument, '
                  'falling back to late assignment...')

        kwargs = copy.deepcopy(kwargs)
        action_service = kwargs.pop('action_service', None)
        action_instance = action_cls(**kwargs)
        action_instance.action_service = action_service

    return action_instance
