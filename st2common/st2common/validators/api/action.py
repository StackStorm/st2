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
import six

from st2common.exceptions.apivalidation import ValueValidationException
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common import log as logging
from st2common.util.action_db import get_runnertype_by_name
from st2common.util import schema as util_schema
from st2common.content.utils import get_packs_base_paths
from st2common.content.utils import check_pack_content_directory_exists
from st2common.models.system.common import ResourceReference
from six.moves import range

__all__ = ["validate_action", "get_runner_model"]


LOG = logging.getLogger(__name__)


def validate_action(action_api, runner_type_db=None):
    """
    :param runner_type_db: RunnerTypeDB object belonging to this action. If not provided, it's
                           retrieved from the database.
    :type runner_type_db: :class:`RunnerTypeDB`
    """
    if not runner_type_db:
        runner_db = get_runner_model(action_api)
    else:
        runner_db = runner_type_db

    # Check if pack is valid.
    if not _is_valid_pack(action_api.pack):
        packs_base_paths = get_packs_base_paths()
        packs_base_paths = ",".join(packs_base_paths)
        msg = (
            'Content pack "%s" is not found or doesn\'t contain actions directory. '
            "Searched in: %s" % (action_api.pack, packs_base_paths)
        )
        raise ValueValidationException(msg)

    # Check if parameters defined are valid.
    action_ref = ResourceReference.to_string_reference(
        pack=action_api.pack, name=action_api.name
    )
    _validate_parameters(action_ref, action_api.parameters, runner_db.runner_parameters)


def get_runner_model(action_api):
    runner_db = None
    # Check if runner exists.
    try:
        runner_db = get_runnertype_by_name(action_api.runner_type)
    except StackStormDBObjectNotFoundError:
        msg = (
            "RunnerType %s is not found. If you are using old and deprecated runner name, you "
            "need to switch to a new one. For more information, please see "
            "https://docs.stackstorm.com/upgrade_notes.html#st2-v0-9"
            % (action_api.runner_type)
        )
        raise ValueValidationException(msg)
    return runner_db


def _is_valid_pack(pack):
    return check_pack_content_directory_exists(pack=pack, content_type="actions")


def _validate_parameters(action_ref, action_params=None, runner_params=None):
    position_params = {}
    for action_param, action_param_meta in six.iteritems(action_params):
        # Check if overridden runner parameters are permitted.
        if action_param in runner_params:
            for action_param_attr, value in six.iteritems(action_param_meta):
                util_schema.validate_runner_parameter_attribute_override(
                    action_ref,
                    action_param,
                    action_param_attr,
                    value,
                    runner_params[action_param].get(action_param_attr),
                )

        if "position" in action_param_meta:
            pos = action_param_meta["position"]
            param = position_params.get(pos, None)
            if param:
                msg = (
                    "Parameters %s and %s have same position %d."
                    % (action_param, param, pos)
                    + " Position values have to be unique."
                )
                raise ValueValidationException(msg)
            else:
                position_params[pos] = action_param

        if "immutable" in action_param_meta:
            if action_param in runner_params:
                runner_param_meta = runner_params[action_param]
                if "immutable" in runner_param_meta:
                    msg = (
                        "Param %s is declared immutable in runner. " % action_param
                        + "Cannot override in action."
                    )
                    raise ValueValidationException(msg)
                if (
                    "default" not in action_param_meta
                    and "default" not in runner_param_meta
                ):
                    msg = "Immutable param %s requires a default value." % action_param
                    raise ValueValidationException(msg)
            else:
                if "default" not in action_param_meta:
                    msg = "Immutable param %s requires a default value." % action_param
                    raise ValueValidationException(msg)

    return _validate_position_values_contiguous(position_params)


def _validate_position_values_contiguous(position_params):
    if not position_params:
        return True

    positions = sorted(position_params.keys())
    contiguous = positions == list(range(min(positions), max(positions) + 1))

    if not contiguous:
        msg = "Positions supplied %s for parameters are not contiguous." % positions
        raise ValueValidationException(msg)

    return True
