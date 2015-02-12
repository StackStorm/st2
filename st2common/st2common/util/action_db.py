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

from collections import OrderedDict

from mongoengine import ValidationError
import six

from st2common import log as logging
from st2common.constants.action import (ACTIONEXEC_STATUSES)
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.action import (RunnerType, Action, ActionExecution)

LOG = logging.getLogger(__name__)


def get_runnertype_by_id(runnertype_id):
    """
        Get RunnerType by id.

        On error, raise StackStormDBObjectNotFoundError
    """
    try:
        runnertype = RunnerType.get_by_id(runnertype_id)
    except (ValueError, ValidationError) as e:
        LOG.warning('Database lookup for runnertype with id="%s" resulted in '
                    'exception: %s', runnertype_id, e)
        raise StackStormDBObjectNotFoundError('Unable to find runnertype with '
                                              'id="%s"' % runnertype_id)

    return runnertype


def get_runnertype_by_name(runnertype_name):
        """
            Get an runnertype by name.
            On error, raise ST2ObjectNotFoundError.
        """
        try:
            runnertypes = RunnerType.query(name=runnertype_name)
        except (ValueError, ValidationError) as e:
            LOG.error('Database lookup for name="%s" resulted in exception: %s',
                      runnertype_name, e)
            raise StackStormDBObjectNotFoundError('Unable to find runnertype with name="%s"'
                                                  % runnertype_name)

        if not runnertypes:
            LOG.error('Database lookup for RunnerType with name="%s" produced no results',
                      runnertype_name)
            raise StackStormDBObjectNotFoundError('Unable to find RunnerType with name="%s"'
                                                  % runnertype_name)

        if len(runnertypes) > 1:
            LOG.warning('More than one RunnerType returned from DB lookup by name. '
                        'Result list is: %s', runnertypes)

        return runnertypes[0]


def get_action_by_id(action_id):
    """
        Get Action by id.

        On error, raise StackStormDBObjectNotFoundError
    """
    action = None

    try:
        action = Action.get_by_id(action_id)
    except (ValueError, ValidationError) as e:
        LOG.warning('Database lookup for action with id="%s" resulted in '
                    'exception: %s', action_id, e)
        raise StackStormDBObjectNotFoundError('Unable to find action with '
                                              'id="%s"' % action_id)

    return action


def get_action_by_ref(ref):
    """
    Returns the action object from db given a string ref.

    :param ref: Reference to the trigger type db object.
    :type ref: ``str``

    :rtype action: ``object``
    """
    try:
        return Action.get_by_ref(ref)
    except ValueError as e:
        LOG.debug('Database lookup for ref="%s" resulted ' +
                  'in exception : %s.', ref, e, exc_info=True)
        return None


def get_actionexec_by_id(actionexec_id):
    """
        Get ActionExecution by id.

        On error, raise ST2DBObjectNotFoundError.
    """
    actionexec = None

    try:
        actionexec = ActionExecution.get_by_id(actionexec_id)
    except (ValidationError, ValueError) as e:
        LOG.error('Database lookup for actionexecution with id="%s" resulted in '
                  'exception: %s', actionexec_id, e)
        raise StackStormDBObjectNotFoundError('Unable to find actionexecution with '
                                              'id="%s"' % actionexec_id)

    return actionexec


def update_actionexecution_status(status=None, result=None, context=None,
                                  end_timestamp=None, actionexec_id=None,
                                  actionexec_db=None):
    """
        Update the status of the specified ActionExecution to the value provided in
        new_status.

        The ActionExecution may be specified using either actionexec_id, or as an
        actionexec_db instance.
    """

    if (actionexec_id is None) and (actionexec_db is None):
        raise ValueError('Must specify an actionexec_id or an actionexec_db when '
                         'calling update_actionexecution_status')

    if actionexec_db is None:
        actionexec_db = get_actionexec_by_id(actionexec_id)

    if status not in ACTIONEXEC_STATUSES:
        raise ValueError('Attempting to set status for ActionExecution "%s" '
                         'to unknown status string. Unknown status is "%s"',
                         actionexec_db, status)

    LOG.debug('Updating ActionExection: "%s" with status="%s"',
              actionexec_db, status)

    actionexec_db.status = status

    if result:
        actionexec_db.result = result

    if context:
        actionexec_db.context.update(context)

    if end_timestamp:
        actionexec_db.end_timestamp = end_timestamp

    actionexec_db = ActionExecution.add_or_update(actionexec_db)
    LOG.debug('Updated status for ActionExecution object: %s', actionexec_db)

    return actionexec_db


def get_args(action_parameters, action_db):
    """
    :return: (positional_args, named_args)
    :rtype: (``str``, ``dict``)
    """
    position_args_dict = _get_position_arg_dict(action_parameters, action_db)

    positional_args = []
    positional_args_keys = set()
    for pos, arg in six.iteritems(position_args_dict):
        positional_args.append(str(action_parameters.get(arg)))
        positional_args_keys.add(arg)
    positional_args = ' '.join(positional_args)  # convert to string.

    named_args = {}
    for param in action_parameters:
        if param not in positional_args_keys:
            named_args[param] = action_parameters.get(param)

    return positional_args, named_args


def _get_position_arg_dict(action_parameters, action_db):
    action_db_params = action_db.parameters

    args_dict = {}
    for param in action_db_params:
        param_meta = action_db_params.get(param, None)
        if param_meta is not None:
            pos = param_meta.get('position')
            if pos is not None:
                args_dict[pos] = param
    args_dict = OrderedDict(sorted(args_dict.items()))
    return args_dict
