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
import six

from st2common import log as logging
from st2common.util import action_db as action_db_util
from st2common.util.casts import get_cast

LOG = logging.getLogger(__name__)


def _merge_param_meta_values(action_meta=None, runner_meta=None):
    runner_meta_keys = runner_meta.keys() if runner_meta else []
    action_meta_keys = action_meta.keys() if action_meta else []
    all_keys = set(runner_meta_keys).union(set(action_meta_keys))

    merged_meta = {}

    # ?? Runner immutable param's meta shouldn't be allowed to be modified by action whatsoever.
    if runner_meta and runner_meta.get('immutable', False):
        merged_meta = runner_meta

    for key in all_keys:
        if key in action_meta_keys and key not in runner_meta_keys:
            merged_meta[key] = action_meta[key]
        elif key in runner_meta_keys and key not in action_meta_keys:
            merged_meta[key] = runner_meta[key]
        else:
            if key in ['immutable']:
                merged_meta[key] = runner_meta.get(key, False) or action_meta.get(key, False)
            else:
                merged_meta[key] = action_meta.get(key)
    return merged_meta


def get_params_view(action_db=None, runner_db=None, merged_only=False):
    runner_params = copy.deepcopy(runner_db.runner_parameters) if runner_db else {}
    action_params = copy.deepcopy(action_db.parameters) if action_db else {}

    parameters = set(runner_params.keys()).union(set(action_params.keys()))

    merged_params = {}
    for param in parameters:
        merged_params[param] = _merge_param_meta_values(action_meta=action_params.get(param),
                                                        runner_meta=runner_params.get(param))

    if merged_only:
        return merged_params

    def is_required(param_meta):
        return param_meta.get('required', False)

    def is_immutable(param_meta):
        return param_meta.get('immutable', False)

    immutable = {param for param in parameters if is_immutable(merged_params.get(param))}
    required = {param for param in parameters if is_required(merged_params.get(param))}
    required = required - immutable
    optional = parameters - required - immutable

    required_params = {k: merged_params[k] for k in required}
    optional_params = {k: merged_params[k] for k in optional}
    immutable_params = {k: merged_params[k] for k in immutable}

    return (required_params, optional_params, immutable_params)


def cast_params(action_ref, params, cast_overrides=None):
    """
    """
    params = params or {}
    action_db = action_db_util.get_action_by_ref(action_ref)

    if not action_db:
        raise ValueError('Action with ref "%s" doesn\'t exist' % (action_ref))

    action_parameters_schema = action_db.parameters
    runnertype_db = action_db_util.get_runnertype_by_name(action_db.runner_type['name'])
    runner_parameters_schema = runnertype_db.runner_parameters
    # combine into 1 list of parameter schemas
    parameters_schema = {}
    if runner_parameters_schema:
        parameters_schema.update(runner_parameters_schema)
    if action_parameters_schema:
        parameters_schema.update(action_parameters_schema)
    # cast each param individually
    for k, v in six.iteritems(params):
        parameter_schema = parameters_schema.get(k, None)
        if not parameter_schema:
            LOG.debug('Will skip cast of param[name: %s, value: %s]. No schema.', k, v)
            continue
        parameter_type = parameter_schema.get('type', None)
        if not parameter_type:
            LOG.debug('Will skip cast of param[name: %s, value: %s]. No type.', k, v)
            continue
        # Pick up cast from teh override and then from the system suppied ones.
        cast = cast_overrides.get(parameter_type, None) if cast_overrides else None
        if not cast:
            cast = get_cast(cast_type=parameter_type)
        if not cast:
            LOG.debug('Will skip cast of param[name: %s, value: %s]. No cast for %s.', k, v,
                      parameter_type)
            continue
        LOG.debug('Casting param: %s of type %s to type: %s', v, type(v), parameter_type)

        try:
            params[k] = cast(v)
        except Exception as e:
            v_type = type(v).__name__
            msg = ('Failed to cast value "%s" (type: %s) for parameter "%s" of type "%s": %s. '
                   'Perhaphs the value is of an invalid type?' %
                   (v, v_type, k, parameter_type, str(e)))
            raise ValueError(msg)

    return params


def validate_action_parameters(action_ref, inputs):
    input_set = set(inputs.keys())

    # Get the list of action and runner parameters.
    parameters = action_db_util.get_action_parameters_specs(action_ref)

    # Check required parameters that have no default defined.
    required = set([param for param, meta in six.iteritems(parameters)
                    if meta.get('required', False) and 'default' not in meta])

    requires = sorted(required.difference(input_set))

    # Check unexpected parameters:
    unexpected = sorted(input_set.difference(set(parameters.keys())))

    return requires, unexpected
