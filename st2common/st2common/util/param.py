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

import six
import networkx as nx

from jinja2 import meta
from st2common import log as logging
from st2common.constants.action import ACTION_CONTEXT_KV_PREFIX
from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.exceptions.param import ParamException
from st2common.services.keyvalues import KeyValueLookup
from st2common.util.casts import get_cast
from st2common.util.compat import to_unicode
from st2common.util import jinja as jinja_utils


LOG = logging.getLogger(__name__)
ENV = jinja_utils.get_jinja_environment()

__all__ = [
    'render_live_params',
    'render_final_params',
]


def _split_params(runner_parameters, action_parameters, mixed_params):
    def pf(params, skips):
        result = {k: v for k, v in six.iteritems(mixed_params)
                  if k in params and k not in skips}
        return result
    return (pf(runner_parameters, {}), pf(action_parameters, runner_parameters))


def _cast_params(rendered, parameter_schemas):
    '''
    It's just here to make tests happy
    '''
    casted_params = {}
    for k, v in six.iteritems(rendered):
        casted_params[k] = _cast(v, parameter_schemas[k] or {})
    return casted_params


def _cast(v, parameter_schema):
    if v is None or not parameter_schema:
        return v

    parameter_type = parameter_schema.get('type', None)
    if not parameter_type:
        return v

    cast = get_cast(cast_type=parameter_type)
    if not cast:
        return v

    return cast(v)


def _create_graph(action_context):
    '''
    Creates a generic directed graph for depencency tree and fills it with basic context variables
    '''
    G = nx.DiGraph()
    G.add_node(SYSTEM_SCOPE, value=KeyValueLookup(scope=SYSTEM_SCOPE))
    G.add_node(ACTION_CONTEXT_KV_PREFIX, value=action_context)
    return G


def _process(G, name, value):
    '''
    Determines whether parameter is a template or a value. Adds graph nodes and edges accordingly.
    '''
    # Jinja defaults to ascii parser in python 2.x unless you set utf-8 support on per module level
    # Instead we're just assuming every string to be a unicode string
    if isinstance(value, str):
        value = to_unicode(value)

    complex_value_str = None
    if isinstance(value, list) or isinstance(value, dict):
        complex_value_str = str(value)

    is_jinja_expr = (
        jinja_utils.is_jinja_expression(value) or jinja_utils.is_jinja_expression(
            complex_value_str
        )
    )

    if is_jinja_expr:
        G.add_node(name, template=value)

        template_ast = ENV.parse(value)
        LOG.debug('Template ast: %s', template_ast)
        # Dependencies of the node represent jinja variables used in the template
        # We're connecting nodes with an edge for every depencency to traverse them
        # in the right order and also make sure that we don't have missing or cyclic
        # dependencies upfront.
        dependencies = meta.find_undeclared_variables(template_ast)
        LOG.debug('Dependencies: %s', dependencies)
        if dependencies:
            for dependency in dependencies:
                G.add_edge(dependency, name)
    else:
        G.add_node(name, value=value)


def _process_defaults(G, schemas):
    '''
    Process dependencies for parameters default values in the order schemas are defined.
    '''
    for schema in schemas:
        for name, value in six.iteritems(schema):
            absent = name not in G.node
            is_none = G.node.get(name, {}).get('value') is None
            immutable = value.get('immutable', False)
            if absent or is_none or immutable:
                _process(G, name, value.get('default'))


def _validate(G):
    '''
    Validates dependency graph to ensure it has no missing or cyclic dependencies
    '''
    for name in G.nodes():
        if 'value' not in G.node[name] and 'template' not in G.node[name]:
            msg = 'Dependecy unsatisfied in %s' % name
            raise ParamException(msg)

    if not nx.is_directed_acyclic_graph(G):
        msg = 'Cyclic dependecy found'
        raise ParamException(msg)


def _render(node, render_context):
    '''
    Render the node depending on its type
    '''
    if 'template' in node:
        LOG.debug('Rendering node: %s with context: %s', node, render_context)
        return ENV.from_string(node['template']).render(render_context)
    if 'value' in node:
        return node['value']


def _resolve_dependencies(G):
    '''
    Traverse the dependency graph starting from resolved nodes
    '''
    context = {}
    for name in nx.topological_sort(G):
        node = G.node[name]
        try:
            if 'template' in node and isinstance(node.get('template', None), list):
                rendered_list = list()
                for template in G.node[name]['template']:
                    rendered_list.append(
                        _render(dict(template=template), context)
                    )
                context[name] = rendered_list
            else:
                context[name] = _render(node, context)
        except Exception as e:
            LOG.debug('Failed to render %s: %s', name, e, exc_info=True)
            msg = 'Failed to render parameter "%s": %s' % (name, str(e))
            raise ParamException(msg)
    return context


def _cast_params_from(params, context, schemas):
    '''
    Pick a list of parameters from context and cast each of them according to the schemas provided
    '''
    result = {}
    for name in params:
        param_schema = {}
        for schema in schemas:
            if name in schema:
                param_schema = schema[name]
        result[name] = _cast(context[name], param_schema)
    return result


def render_live_params(runner_parameters, action_parameters, params, action_context):
    '''
    Renders list of parameters. Ensures that there's no cyclic or missing dependencies. Returns a
    dict of plain rendered parameters.
    '''
    G = _create_graph(action_context)

    [_process(G, name, value) for name, value in six.iteritems(params)]
    _process_defaults(G, [action_parameters, runner_parameters])
    _validate(G)

    context = _resolve_dependencies(G)
    live_params = _cast_params_from(params, context, [action_parameters, runner_parameters])

    return live_params


def render_final_params(runner_parameters, action_parameters, params, action_context):
    '''
    Renders missing parameters required for action to execute. Treats parameters from the dict as
    plain values instead of trying to render them again. Returns dicts for action and runner
    parameters.
    '''
    G = _create_graph(action_context)

    # by that point, all params should already be resolved so any template should be treated value
    [G.add_node(name, value=value) for name, value in six.iteritems(params)]
    _process_defaults(G, [action_parameters, runner_parameters])
    _validate(G)

    context = _resolve_dependencies(G)
    context = _cast_params_from(context, context, [action_parameters, runner_parameters])

    return _split_params(runner_parameters, action_parameters, context)


def get_finalized_params(runnertype_parameter_info, action_parameter_info, liveaction_parameters,
                         action_context):
    '''
    Left here to keep tests running. Later we would need to split tests so they start testing each
    function separately.
    '''
    params = render_live_params(runnertype_parameter_info, action_parameter_info,
                                liveaction_parameters, action_context)
    return render_final_params(runnertype_parameter_info, action_parameter_info, params,
                               action_context)
