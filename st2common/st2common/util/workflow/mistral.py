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
import json
import re

import six
import yaml

from st2common.exceptions.workflow import WorkflowDefinitionException
from st2common import log as logging
from st2common.models.system.common import ResourceReference
from st2common.models.utils import action_param_utils
from st2common.util import action_db as action_utils


LOG = logging.getLogger(__name__)


CMD_PTRN = re.compile("^[\w\.]+[^=\s\"]*")

INLINE_YAQL = '<%.*?%>'
_ALL_IN_BRACKETS = "\[.*\]\s*"
_ALL_IN_QUOTES = "\"[^\"]*\"\s*"
_ALL_IN_APOSTROPHES = "'[^']*'\s*"
_DIGITS = "\d+"
_TRUE = "true"
_FALSE = "false"
_NULL = "null"

ALL = (
    _ALL_IN_QUOTES, _ALL_IN_APOSTROPHES, INLINE_YAQL,
    _ALL_IN_BRACKETS, _TRUE, _FALSE, _NULL, _DIGITS
)

PARAMS_PTRN = re.compile("([\w]+)=(%s)" % "|".join(ALL))

SPEC_TYPES = {
    'adhoc': {
        'action_key': 'base',
        'input_key': 'base-input'
    },
    'task': {
        'action_key': 'action',
        'input_key': 'input'
    }
}


def _parse_cmd_and_input(cmd_str):
    cmd_matcher = CMD_PTRN.search(cmd_str)

    if not cmd_matcher:
        raise ValueError("Invalid action/workflow task property: %s" % cmd_str)

    cmd = cmd_matcher.group()

    params = {}
    for k, v in re.findall(PARAMS_PTRN, cmd_str):
        # Remove embracing quotes.
        v = v.strip()
        if v[0] == '"' or v[0] == "'":
            v = v[1:-1]
        else:
            try:
                v = json.loads(v)
            except Exception:
                pass

        params[k] = v

    return cmd, params


def _merge_dicts(left, right):
    if left is None:
        return right

    if right is None:
        return left

    for k, v in right.iteritems():
        if k not in left:
            left[k] = v
        else:
            left_v = left[k]

            if isinstance(left_v, dict) and isinstance(v, dict):
                _merge_dicts(left_v, v)

    return left


def _eval_inline_params(spec, action_key, input_key):
    action_str = spec.get(action_key)
    command, inputs = _parse_cmd_and_input(action_str)
    if inputs:
        spec[action_key] = command
        if input_key not in spec:
            spec[input_key] = {}
            _merge_dicts(spec[input_key], inputs)


def _validate_action_parameters(name, action, action_params):
    requires, unexpected = action_param_utils.validate_action_parameters(action.ref, action_params)

    if requires:
        raise WorkflowDefinitionException('Missing required parameters in "%s" for action "%s": '
                                          '"%s"' % (name, action.ref, '", "'.join(requires)))

    if unexpected:
        raise WorkflowDefinitionException('Unexpected parameters in "%s" for action "%s": '
                                          '"%s"' % (name, action.ref, '", "'.join(unexpected)))


def _transform_action(name, spec):

    action_key, input_key = None, None

    for spec_type, spec_meta in six.iteritems(SPEC_TYPES):
        if spec_meta['action_key'] in spec:
            action_key = spec_meta['action_key']
            input_key = spec_meta['input_key']
            break

    if not action_key:
        return

    if spec[action_key] == 'st2.callback':
        raise WorkflowDefinitionException('st2.callback is deprecated.')

    # Convert parameters that are inline (i.e. action: some_action var1={$.value1} var2={$.value2})
    # and split it to action name and input dict as illustrated below.
    #
    # action: some_action
    # input:
    #   var1: <% $.value1 %>
    #   var2: <% $.value2 %>
    #
    # This step to separate the action name and the input parameters is required
    # to wrap them with the st2.action proxy.
    #
    # action: st2.action
    # input:
    #   ref: some_action
    #   parameters:
    #     var1: <% $.value1 %>
    #     var2: <% $.value2 %>
    _eval_inline_params(spec, action_key, input_key)

    transformed = (spec[action_key] == 'st2.action')

    action_ref = spec[input_key]['ref'] if transformed else spec[action_key]

    action = None

    # Identify if action is a registered StackStorm action.
    if action_ref and ResourceReference.is_resource_reference(action_ref):
        action = action_utils.get_action_by_ref(ref=action_ref)

    # If action is a registered StackStorm action, then wrap the
    # action with the st2 proxy and validate the action input.
    if action:
        if not transformed:
            spec[action_key] = 'st2.action'
            action_input = spec.get(input_key)
            spec[input_key] = {'ref': action_ref}
            if action_input:
                spec[input_key]['parameters'] = action_input

        action_input = spec.get(input_key, {})
        action_params = action_input.get('parameters', {})
        _validate_action_parameters(name, action, action_params)


def transform_definition(definition):
    # If definition is a dictionary, there is no need to load from YAML.
    is_dict = isinstance(definition, dict)
    spec = copy.deepcopy(definition) if is_dict else yaml.safe_load(definition)

    # Transform adhoc actions
    for action_name, action_spec in six.iteritems(spec.get('actions', {})):
        _transform_action(action_name, action_spec)

    # Determine if definition is a workbook or workflow
    is_workbook = 'workflows' in spec

    # Transform tasks
    if is_workbook:
        for workflow_name, workflow_spec in six.iteritems(spec.get('workflows', {})):
            if 'tasks' in workflow_spec:
                for task_name, task_spec in six.iteritems(workflow_spec.get('tasks')):
                    _transform_action(task_name, task_spec)
    else:
        for key, value in six.iteritems(spec):
            if 'tasks' in value:
                for task_name, task_spec in six.iteritems(value.get('tasks')):
                    _transform_action(task_name, task_spec)

    # Return the same type as original input.
    return spec if is_dict else yaml.safe_dump(spec, default_flow_style=False)
