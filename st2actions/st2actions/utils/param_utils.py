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

import six

from jinja2 import Template, Environment, StrictUndefined, meta, exceptions
from st2common import log as logging
from st2common.constants.action import ACTION_CONTEXT_KV_PREFIX
from st2common.constants.system import SYSTEM_KV_PREFIX
from st2common.exceptions import actionrunner
from st2common.services.keyvalues import KeyValueLookup
from st2common.util.casts import get_cast
from st2common.util.compat import to_unicode


LOG = logging.getLogger(__name__)

__all__ = [
    'get_finalized_params',
]


def _split_params(runner_parameters, action_parameters, mixed_params):
    def pf(params, skips):
        result = {k: v for k, v in six.iteritems(mixed_params)
                  if k in params and k not in skips}
        return result
    return (pf(runner_parameters, {}), pf(action_parameters, runner_parameters))


def _get_resolved_runner_params(runner_parameters, action_parameters,
                                actionexec_runner_parameters):
    # Runner parameters should use the defaults from the RunnerType object.
    # The runner parameter defaults may be overridden by values provided in
    # the Action and liveaction.

    # Create runner parameter by merging default values with dynamic values
    resolved_params = {k: v['default'] if 'default' in v else None
                       for k, v in six.iteritems(runner_parameters)}

    # pick overrides from action_parameters & actionexec_runner_parameters
    for param_name, param_value in six.iteritems(runner_parameters):
        # No override if param is immutable
        if param_value.get('immutable', False):
            continue

        # Check if param exists in action_parameters and if it has a default value then
        # pickup the override.
        if param_name in action_parameters:
            action_param = action_parameters[param_name]
            if 'default' in action_param:
                resolved_params[param_name] = action_param['default']

            # No further override (from liveaction) if param is immutable
            if action_param.get('immutable', False):
                continue

        # Finally pick up override from actionexec_runner_parameters
        if param_name in actionexec_runner_parameters:
            resolved_params[param_name] = actionexec_runner_parameters[param_name]

    return resolved_params


def _get_resolved_action_params(runner_parameters, action_parameters,
                                actionexec_action_parameters):
    # Create action parameters by merging default values with dynamic values
    resolved_params = {k: v['default'] if 'default' in v else None
                       for k, v in six.iteritems(action_parameters)
                       if k not in runner_parameters}

    # pick overrides from actionexec_action_parameters
    for param_name, param_value in six.iteritems(action_parameters):
        # No override if param is immutable
        if param_value.get('immutable', False):
            continue
        if param_name in actionexec_action_parameters and param_name not in runner_parameters:
            resolved_params[param_name] = actionexec_action_parameters[param_name]

    return resolved_params


def _get_resolved_params(runnertype_parameter_info, action_parameter_info, actionexec_parameters):
    '''
    Looks at the parameter values from runner, action and action execution to fully resolve the
    values. Resolution is the process of determinig the value of a parameter by taking into
    consideration default, immutable and user supplied values.
    '''
    # Runner parameters should use the defaults from the RunnerType object.
    # The runner parameter defaults may be overridden by values provided in
    # the Action and liveaction.
    actionexec_runner_parameters, actionexec_action_parameters = _split_params(
        runnertype_parameter_info, action_parameter_info, actionexec_parameters)
    runner_params = _get_resolved_runner_params(runnertype_parameter_info,
                                                action_parameter_info,
                                                actionexec_runner_parameters)
    action_params = _get_resolved_action_params(runnertype_parameter_info,
                                                action_parameter_info,
                                                actionexec_action_parameters)

    return runner_params, action_params


def _is_template(template_str):
    template_str = to_unicode(template_str)
    template = Template(template_str)
    try:
        return template_str != template.render({})
    except exceptions.UndefinedError:
        return True


def _renderable_context_param_split(action_parameters, runner_parameters, base_context=None):
    # To render the params it is necessary to combine the params together so that cross
    # parameter category references are resolved.
    renderable_params = {}
    # shallow copy since this will be updated
    context_params = copy.copy(base_context) if base_context else {}

    def do_render_context_split(source_params):
        '''
        Will split the supplied source_params into renderable_params and context_params. As part of
        the split also makes sure that the all params are essentially strings.
        '''
        for k, v in six.iteritems(source_params):
            renderable_v = v
            # dict and list to be converted to str
            if isinstance(renderable_v, dict) or isinstance(renderable_v, list):
                renderable_v = json.dumps(renderable_v)
            # only str can contain templates
            if (isinstance(renderable_v, str) or isinstance(renderable_v, unicode)) and \
               _is_template(renderable_v):
                renderable_params[k] = renderable_v
            elif isinstance(v, dict) or isinstance(v, list):
                # For context use the renderable value for dict and list params. The template
                # rendering by jinja yields a non json.loads compatible value leading to issues
                # while performing casts.
                context_params[k] = renderable_v
            else:
                # For context use the original value.
                context_params[k] = v

    do_render_context_split(action_parameters)
    do_render_context_split(runner_parameters)

    return (renderable_params, context_params)


def _check_availability(param, param_dependencies, renderable_params, context):
    for dependency in param_dependencies:
        if dependency not in renderable_params and dependency not in context:
            return False
    return True


def _check_cyclic(dep_chain, dependencies):
    last_idx = len(dep_chain) - 1
    last_value = dep_chain[last_idx]
    for dependency in dependencies.get(last_value, []):
        if dependency in dep_chain:
            dep_chain.append(dependency)
            return False
        dep_chain.append(dependency)
        if not _check_cyclic(dep_chain, dependencies):
            return False
        dep_chain.pop()
    return True


def _validate_dependencies(renderable_params, context):
    '''
    Validates dependencies between the parameters.
    e.g.
    {
        'a': '{{b}}',
        'b': '{{a}}'
    }
    In this example 'a' requires 'b' for template rendering and vice-versa. There is no way for
    these templates to be rendered and will be flagged with an ActionRunnerException.
    '''
    env = Environment(undefined=StrictUndefined)
    dependencies = {}
    for k, v in six.iteritems(renderable_params):
        template_ast = env.parse(v)
        dependencies[k] = meta.find_undeclared_variables(template_ast)

    for k, v in six.iteritems(dependencies):
        if not _check_availability(k, v, renderable_params, context):
            msg = 'Dependecy unsatisfied - %s: %s.' % (k, v)
            raise actionrunner.ActionRunnerException(msg)
        dep_chain = []
        dep_chain.append(k)
        if not _check_cyclic(dep_chain, dependencies):
            msg = 'Cyclic dependecy found - %s.' % dep_chain
            raise actionrunner.ActionRunnerException(msg)


def _do_render_params(renderable_params, context):
    '''
    Will render the params per the context and will return best attempt to render. Render attempts
    with missing params will leave blanks.
    '''
    if not renderable_params:
        return renderable_params
    _validate_dependencies(renderable_params, context)
    env = Environment(undefined=StrictUndefined)
    rendered_params = {}
    rendered_params.update(context)

    # Maps parameter key to render exception
    # We save the exception so we can throw a more meaningful exception at the end if rendering of
    # some parameter fails
    parameter_render_exceptions = {}

    num_parameters = len(renderable_params) + len(context)
    # After how many attempts at failing to render parameter we should bail out
    max_rendered_parameters_unchanged_count = num_parameters
    rendered_params_unchanged_count = 0

    while len(renderable_params) != 0:
        renderable_params_pre_loop = renderable_params.copy()
        for k, v in six.iteritems(renderable_params):
            template = env.from_string(v)

            try:
                rendered = template.render(rendered_params)
                rendered_params[k] = rendered

                if k in parameter_render_exceptions:
                    del parameter_render_exceptions[k]
            except Exception as e:
                # Note: This sucks, but because we support multi level and out of order
                # rendering, we can't throw an exception here yet since the parameter could get
                # rendered in future iteration
                LOG.debug('Failed to render %s: %s', k, v, exc_info=True)
                parameter_render_exceptions[k] = e

        for k in rendered_params:
            if k in renderable_params:
                del renderable_params[k]

        if renderable_params_pre_loop == renderable_params:
            rendered_params_unchanged_count += 1

        # Make sure we terminate and don't end up in an infinite loop if we
        # tried to render all the parameters but rendering of some parameters
        # still fails
        if rendered_params_unchanged_count >= max_rendered_parameters_unchanged_count:
            k = parameter_render_exceptions.keys()[0]
            e = parameter_render_exceptions[k]
            msg = 'Failed to render parameter "%s": %s' % (k, str(e))
            raise actionrunner.ActionRunnerException(msg)

    return rendered_params


def _cast_params(rendered, parameter_schemas):
    casted_params = {}
    for k, v in six.iteritems(rendered):
        # Add uncasted first and then override with casted param. Not all params will end up
        # being cast.
        casted_params[k] = v
        # No casting if the value is None. It leads to weird cases like str(None) = 'None'
        # leading to downstream failures as well as int(None) leading to TypeError.
        if v is None:
            continue
        parameter_schema = parameter_schemas.get(k, None)
        if not parameter_schema:
            continue
        parameter_type = parameter_schema.get('type', None)
        if not parameter_type:
            continue
        cast = get_cast(cast_type=parameter_type)
        if not cast:
            continue
        casted_params[k] = cast(v)
    return casted_params


def _get_rendered_params(runner_parameters, action_parameters, action_context,
                        runnertype_parameter_info, action_parameter_info):
    '''
    Renders the templates in runner_parameters and action_parameters. Using the type information
    from *_parameter_info will appropriately cast the parameters.
    '''
    # To render the params it is necessary to combine the params together so that cross
    # parameter category references are also rendered correctly. Particularly in the cases where
    # a runner parameter is overridden in an action it is likely that a runner parameter could
    # depend on an action parameter.
    render_context = {SYSTEM_KV_PREFIX: KeyValueLookup()}
    render_context[ACTION_CONTEXT_KV_PREFIX] = action_context
    renderable_params, context = _renderable_context_param_split(action_parameters,
                                                                 runner_parameters,
                                                                 render_context)
    rendered_params = _do_render_params(renderable_params, context)
    template_free_params = {}
    template_free_params.update(rendered_params)
    template_free_params.update(context)

    r_runner_parameters, r_action_parameters = _split_params(runnertype_parameter_info,
                                                             action_parameter_info,
                                                             template_free_params)

    return (_cast_params(r_runner_parameters, runnertype_parameter_info),
            _cast_params(r_action_parameters, action_parameter_info))


def get_finalized_params(runnertype_parameter_info, action_parameter_info, liveaction_parameters,
                         action_context):
    '''
    Finalize the parameters for an action to execute by doing the following -
        1. Split the parameters into those consumed by runner and action into separate dicts.
        2. Render any templates in the parameters.
    '''
    runner_params, action_params = _get_resolved_params(runnertype_parameter_info,
                                                        action_parameter_info,
                                                        liveaction_parameters)
    runner_params, action_params = _get_rendered_params(runner_params, action_params,
                                                        action_context,
                                                        runnertype_parameter_info,
                                                        action_parameter_info)
    return (runner_params, action_params)
