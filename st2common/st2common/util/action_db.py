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

from typing import Optional
from typing import List

from collections import OrderedDict

from oslo_config import cfg
import six
from mongoengine import ValidationError

from st2common import log as logging
from st2common.constants.action import (
    LIVEACTION_STATUSES,
    LIVEACTION_STATUS_CANCELED,
    LIVEACTION_STATUS_SUCCEEDED,
)
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.action import Action
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.runner import RunnerType
from st2common.metrics.base import get_driver
from st2common.util import output_schema
from st2common.util.jsonify import json_encode

LOG = logging.getLogger(__name__)


__all__ = [
    "get_action_parameters_specs",
    "get_runnertype_by_id",
    "get_runnertype_by_name",
    "get_action_by_id",
    "get_action_by_ref",
    "get_liveaction_by_id",
    "update_liveaction_status",
    "serialize_positional_argument",
    "get_args",
]


def get_action_parameters_specs(action_ref):
    """
    Retrieve parameters specifications schema for the provided action reference.

    Note: This function returns a union of action and action runner parameters.

    :param action_ref: Action reference.
    :type action_ref: ``str``

    :rtype: ``dict``
    """
    action_db = get_action_by_ref(ref=action_ref)

    parameters = {}
    if not action_db:
        return parameters

    runner_type_name = action_db.runner_type["name"]
    runner_type_db = get_runnertype_by_name(runnertype_name=runner_type_name)

    # Runner type parameters should be added first before the action parameters.
    parameters.update(runner_type_db["runner_parameters"])
    parameters.update(action_db.parameters)

    return parameters


def get_runnertype_by_id(runnertype_id):
    """
    Get RunnerType by id.

    On error, raise StackStormDBObjectNotFoundError
    """
    try:
        runnertype = RunnerType.get_by_id(runnertype_id)
    except (ValueError, ValidationError) as e:
        LOG.warning(
            'Database lookup for runnertype with id="%s" resulted in ' "exception: %s",
            runnertype_id,
            e,
        )
        raise StackStormDBObjectNotFoundError(
            "Unable to find runnertype with " 'id="%s"' % runnertype_id
        )

    return runnertype


def get_runnertype_by_name(runnertype_name):
    """
    Get an runnertype by name.
    On error, raise ST2ObjectNotFoundError.
    """
    try:
        runnertypes = RunnerType.query(name=runnertype_name)
    except (ValueError, ValidationError) as e:
        LOG.error(
            'Database lookup for name="%s" resulted in exception: %s',
            runnertype_name,
            e,
        )
        raise StackStormDBObjectNotFoundError(
            'Unable to find runnertype with name="%s"' % runnertype_name
        )

    if not runnertypes:
        raise StackStormDBObjectNotFoundError(
            'Unable to find RunnerType with name="%s"' % runnertype_name
        )

    if len(runnertypes) > 1:
        LOG.warning(
            "More than one RunnerType returned from DB lookup by name. "
            "Result list is: %s",
            runnertypes,
        )

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
        LOG.warning(
            'Database lookup for action with id="%s" resulted in ' "exception: %s",
            action_id,
            e,
        )
        raise StackStormDBObjectNotFoundError(
            "Unable to find action with " 'id="%s"' % action_id
        )

    return action


def get_action_by_ref(ref, only_fields: Optional[List[str]] = None):
    """
    Returns the action object from db given a string ref.

    :param ref: Reference to the trigger type db object.
    :type ref: ``str``

    :param: only_field: Optional lists if fields to retrieve. If not specified, it defaults to all
                        fields.

    :rtype action: ``object``
    """
    try:
        return Action.get_by_ref(ref, only_fields=only_fields)
    except ValueError as e:
        LOG.debug(
            'Database lookup for ref="%s" resulted ' + "in exception : %s.",
            ref,
            e,
            exc_info=True,
        )
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
        LOG.error(
            'Database lookup for LiveAction with id="%s" resulted in ' "exception: %s",
            liveaction_id,
            e,
        )
        raise StackStormDBObjectNotFoundError(
            "Unable to find LiveAction with " 'id="%s"' % liveaction_id
        )

    return liveaction


def update_liveaction_status(
    status=None,
    result=None,
    context=None,
    end_timestamp=None,
    liveaction_id=None,
    runner_info=None,
    liveaction_db=None,
    publish=True,
):
    """
    Update the status of the specified LiveAction to the value provided in
    new_status.

    The LiveAction may be specified using either liveaction_id, or as an
    liveaction_db instance.
    """

    if (liveaction_id is None) and (liveaction_db is None):
        raise ValueError(
            "Must specify an liveaction_id or an liveaction_db when "
            "calling update_LiveAction_status"
        )

    if liveaction_db is None:
        liveaction_db = get_liveaction_by_id(liveaction_id)

    if status not in LIVEACTION_STATUSES:
        raise ValueError(
            'Attempting to set status for LiveAction "%s" '
            'to unknown status string. Unknown status is "%s"' % (liveaction_db, status)
        )

    if (
        result
        and cfg.CONF.system.validate_output_schema
        and status == LIVEACTION_STATUS_SUCCEEDED
    ):
        action_db = get_action_by_ref(liveaction_db.action)
        runner_db = get_runnertype_by_name(action_db.runner_type["name"])
        result, status = output_schema.validate_output(
            runner_db.output_schema,
            action_db.output_schema,
            result,
            status,
            runner_db.output_key,
        )

    # If liveaction_db status is set then we need to decrement the counter
    # because it is transitioning to a new state
    if liveaction_db.status:
        get_driver().dec_counter("action.executions.%s" % (liveaction_db.status))

    # If status is provided then we need to increment the timer because the action
    # is transitioning into this new state
    if status:
        get_driver().inc_counter("action.executions.%s" % (status))

    extra = {"liveaction_db": liveaction_db}
    LOG.debug(
        'Updating ActionExection: "%s" with status="%s"',
        liveaction_db.id,
        status,
        extra=extra,
    )

    # If liveaction is already canceled, then do not allow status to be updated.
    if (
        liveaction_db.status == LIVEACTION_STATUS_CANCELED
        and status != LIVEACTION_STATUS_CANCELED
    ):
        LOG.info(
            'Unable to update ActionExecution "%s" with status="%s". '
            "ActionExecution is already canceled.",
            liveaction_db.id,
            status,
            extra=extra,
        )
        return liveaction_db

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

    # TODO: This is not efficient. Perform direct partial update and only update
    # manipulated fields
    liveaction_db = LiveAction.add_or_update(liveaction_db)

    LOG.debug("Updated status for LiveAction object.", extra=extra)

    if publish and status != old_status:
        LiveAction.publish_status(liveaction_db)
        LOG.debug("Published status for LiveAction object.", extra=extra)

    return liveaction_db


def serialize_positional_argument(argument_type, argument_value):
    """
    Serialize the provided positional argument.

    Note: Serialization is NOT performed recursively since it doesn't make much
    sense for shell script actions (only the outter / top level value is
    serialized).
    """
    if argument_type in ["string", "number", "float"]:
        if argument_value is None:
            argument_value = six.text_type("")
            return argument_value

        if isinstance(argument_value, (int, float)):
            argument_value = str(argument_value)

        if not isinstance(argument_value, six.text_type):
            # cast string non-unicode values to unicode
            argument_value = argument_value.decode("utf-8")
    elif argument_type == "boolean":
        # Booleans are serialized as string "1" and "0"
        if argument_value is not None:
            argument_value = "1" if bool(argument_value) else "0"
        else:
            argument_value = ""
    elif argument_type in ["array", "list"]:
        # Lists are serialized a comma delimited string (foo,bar,baz)
        argument_value = ",".join(map(str, argument_value)) if argument_value else ""
    elif argument_type == "object":
        # Objects are serialized as JSON
        argument_value = json_encode(argument_value) if argument_value else ""
    elif argument_type == "null":
        # None / null is serialized as en empty string
        argument_value = ""
    else:
        # Other values are simply cast to unicode string
        argument_value = six.text_type(argument_value) if argument_value else ""

    return argument_value


def get_args(action_parameters, action_db):
    """

    Get and serialize positional and named arguments.

    :return: (positional_args, named_args)
    :rtype: (``str``, ``dict``)
    """
    position_args_dict = _get_position_arg_dict(action_parameters, action_db)

    action_db_parameters = action_db.parameters or {}

    positional_args = []
    positional_args_keys = set()
    for _, arg in six.iteritems(position_args_dict):
        arg_type = action_db_parameters.get(arg, {}).get("type", None)

        # Perform serialization for positional arguments
        arg_value = action_parameters.get(arg, None)
        arg_value = serialize_positional_argument(
            argument_type=arg_type, argument_value=arg_value
        )

        positional_args.append(arg_value)
        positional_args_keys.add(arg)

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
            pos = param_meta.get("position")
            if pos is not None:
                args_dict[pos] = param
    args_dict = OrderedDict(sorted(args_dict.items()))
    return args_dict
