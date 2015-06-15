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
from st2common.constants.action import (LIVEACTION_STATUSES)
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.action import Action
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.runner import RunnerType

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


def get_liveaction_by_id(liveaction_id):
    """
        Get LiveAction by id.

        On error, raise ST2DBObjectNotFoundError.
    """
    liveaction = None

    try:
        liveaction = LiveAction.get_by_id(liveaction_id)
    except (ValidationError, ValueError) as e:
        LOG.error('Database lookup for LiveAction with id="%s" resulted in '
                  'exception: %s', liveaction_id, e)
        raise StackStormDBObjectNotFoundError('Unable to find LiveAction with '
                                              'id="%s"' % liveaction_id)

    return liveaction


def update_liveaction_status(status=None, result=None, context=None, end_timestamp=None,
                             liveaction_id=None, runner_info=None, liveaction_db=None,
                             publish=True):
    """
        Update the status of the specified LiveAction to the value provided in
        new_status.

        The LiveAction may be specified using either liveaction_id, or as an
        liveaction_db instance.
    """

    if (liveaction_id is None) and (liveaction_db is None):
        raise ValueError('Must specify an liveaction_id or an liveaction_db when '
                         'calling update_LiveAction_status')

    if liveaction_db is None:
        liveaction_db = get_liveaction_by_id(liveaction_id)

    if status not in LIVEACTION_STATUSES:
        raise ValueError('Attempting to set status for LiveAction "%s" '
                         'to unknown status string. Unknown status is "%s"',
                         liveaction_db, status)

    extra = {'liveaction_db': liveaction_db}
    LOG.debug('Updating ActionExection: "%s" with status="%s"', liveaction_db.id, status,
              extra=extra)

    old_status = liveaction_db.status
    liveaction_db.status = status

    if result:
        liveaction_db.result = result

    if context:
        liveaction_db.context.update(context)

    if end_timestamp:
        liveaction_db.end_timestamp = end_timestamp

    if runner_info:
        liveaction_db.runner_info = runner_info

    liveaction_db = LiveAction.add_or_update(liveaction_db)

    LOG.debug('Updated status for LiveAction object.', extra=extra)

    if publish and status != old_status:
        LiveAction.publish_status(liveaction_db)
        LOG.debug('Published status for LiveAction object.', extra=extra)

    return liveaction_db


def get_args(action_parameters, action_db):
    """
    :return: (positional_args, named_args)
    :rtype: (``str``, ``dict``)
    """
    position_args_dict = _get_position_arg_dict(action_parameters, action_db)

    positional_args = []
    positional_args_keys = set()
    for _, arg in six.iteritems(position_args_dict):
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
