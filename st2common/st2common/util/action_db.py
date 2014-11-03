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
from st2common.constants.action import (ACTIONEXEC_STATUSES,
                                        ACTION_ID, ACTION_NAME, ACTION_PACK)
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.system.common import ResourceReference
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


def _get_action_by_pack_and_name(pack=None, name=None):
    """
        Get Action by name and pack.

        Query doesn't raise an exception.
    """
    return Action.query(name=name, pack=pack).first()


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


def get_action_by_dict(action_dict):
    """
        Get Action object from DB based on action_dict values.

        action_dict is a dictionary that contains either an "id" field,
        a "name" field", or both fields.

        Returns:
            - Action object found in DB. (None on lookup failure.)
            - modified action_dict with "id" key removed if lookup by
                  id failed.
    """
    action = None

    if ACTION_ID in action_dict:
        action_id = action_dict[ACTION_ID]
        try:
            action = get_action_by_id(action_id)
            if (ACTION_NAME not in action_dict or
                    action_dict[ACTION_NAME] != getattr(action, ACTION_NAME)):
                action_dict[ACTION_NAME] = getattr(action, ACTION_NAME)
        except StackStormDBObjectNotFoundError:
            LOG.info('Action not found by id, falling back to lookup by name and '
                     'removing action id from Action Execution.')
            del action_dict[ACTION_ID]
        else:
            return (action, action_dict)

    if ACTION_NAME in action_dict:
        if ACTION_PACK not in action_dict:
            return (None, {})
        name = action_dict[ACTION_NAME]
        pack = action_dict[ACTION_PACK]

        action = _get_action_by_pack_and_name(pack=pack, name=name)

        if action:
            action_dict[ACTION_ID] = str(getattr(action, ACTION_ID))
            return (action, action_dict)

    # No action found by identifiers in action_dict.
    return (None, {})


def get_action_by_ref(action_ref):
    if (not isinstance(action_ref, str) and not isinstance(action_ref, unicode)
            and not isinstance(action_ref, ResourceReference)):
        raise Exception('Action reference has to be either str or ResourceReference.')

    if isinstance(action_ref, str) or isinstance(action_ref, unicode):
        action_ref = ResourceReference.from_string_reference(ref=action_ref)

    return _get_action_by_pack_and_name(name=action_ref.name, pack=action_ref.pack)


def update_actionexecution_status(new_status, actionexec_id=None, actionexec_db=None):
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

    if new_status not in ACTIONEXEC_STATUSES:
        raise ValueError('Attempting to set status for ActionExecution "%s" '
                         'to unknown status string. Unknown status is "%s"',
                         actionexec_db, new_status)

    LOG.debug('Updating ActionExection: "%s" with status="%s"',
              actionexec_db, new_status)
    actionexec_db.status = new_status
    actionexec_db = ActionExecution.add_or_update(actionexec_db)
    LOG.debug('Updated status for ActionExecution object: %s', actionexec_db)
    return actionexec_db


def get_args(action_parameters, action_db):
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
