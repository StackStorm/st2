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
from st2common.constants.system import SYSTEM_KV_PREFIX
from st2common.exceptions.param import ParamException
from st2common.services.keyvalues import KeyValueLookup
from st2common.util.casts import get_cast
from st2common.util.compat import to_unicode
from st2common.util import jinja as jinja_utils


LOG = logging.getLogger(__name__)

__all__ = [
    'render_live_params',
    'render_final_params',
    'get_finalized_params',
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


def _process(G, name, value):
    '''
    Determines whether parameter is a template or a value. Adds graph nodes and edges accordingly.
    '''
    env = jinja_utils.get_jinja_environment()
    if isinstance(value, str):
        value = to_unicode(value)
    template_ast = env.parse(value)
    dependencies = meta.find_undeclared_variables(template_ast)
    if dependencies:
        G.add_node(name, template=value)
        for dependency in dependencies:
            G.add_edge(dependency, name)
    else:
        G.add_node(name, value=value)


def render_live_params(runnertype_parameter_info, action_parameter_info, params, action_context):
    '''
    Renders list of parameters. Ensures that there's no cyclic or missing dependencies. Returns a
    dict of plain rendered parameters.
    '''
    render_context = {}
    env = jinja_utils.get_jinja_environment()

    G = nx.DiGraph()
    G.add_node(SYSTEM_KV_PREFIX, value=KeyValueLookup())
    G.add_node(ACTION_CONTEXT_KV_PREFIX, value=action_context)

    for name, value in six.iteritems(params):
        _process(G, name, value)

    for name, value in six.iteritems(runnertype_parameter_info):
        if name not in params or value.get('immutable', False):
            _process(G, name, value.get('default', None))

    for name, value in six.iteritems(action_parameter_info):
        if name not in params or value.get('immutable', False):
            _process(G, name, value.get('default', None))

    for name in G.nodes():
        if 'value' not in G.node[name] and 'template' not in G.node[name]:
            msg = 'Dependecy unsatisfied in %s' % name
            raise ParamException(msg)

    if not nx.is_directed_acyclic_graph(G):
        msg = 'Cyclic dependecy found'
        raise ParamException(msg)

    for name in nx.topological_sort(G):
        node = G.node[name]
        if 'template' in node:
            try:
                render_context[name] = env.from_string(node['template']).render(render_context)
            except Exception as e:
                LOG.debug('Failed to render %s: %s', name, e, exc_info=True)
                msg = 'Failed to render parameter "%s": %s' % (name, str(e))
                raise ParamException(msg)
        if 'value' in node:
            render_context[name] = node['value']

    result = {}
    for name in params:
        schema = {}
        if (name in action_parameter_info):
            schema = action_parameter_info[name]
        if (name in runnertype_parameter_info):
            schema = runnertype_parameter_info[name]
        result[name] = _cast(render_context[name], schema)

    return result


def render_final_params(runnertype_parameter_info, action_parameter_info, params, action_context):
    '''
    Renders missing parameters required for action to execute. Treats parameters from the dict as
    plain values instead of trying to render them again. Returns dicts for action and runner
    parameters.
    '''
    render_context = {}
    env = jinja_utils.get_jinja_environment()

    G = nx.DiGraph()
    G.add_node(SYSTEM_KV_PREFIX, value=KeyValueLookup())
    G.add_node(ACTION_CONTEXT_KV_PREFIX, value=action_context)

    for name, value in six.iteritems(params):
        # by that point, all params should already be resolved so any template should be treated as
        # a value
        G.add_node(name, value=value)

    for name, value in six.iteritems(runnertype_parameter_info):
        if name not in params or value.get('immutable', False):
            _process(G, name, value.get('default', None))

    for name, value in six.iteritems(action_parameter_info):
        if name not in params or value.get('immutable', False):
            _process(G, name, value.get('default', None))

    for name in G.nodes():
        if 'value' not in G.node[name] and 'template' not in G.node[name]:
            msg = 'Dependecy unsatisfied in %s' % name
            raise ParamException(msg)

    if not nx.is_directed_acyclic_graph(G):
        msg = 'Cyclic dependecy found'
        raise ParamException(msg)

    for name in nx.topological_sort(G):
        node = G.node[name]
        schema = {}
        if (name in action_parameter_info):
            schema = action_parameter_info[name]
        if (name in runnertype_parameter_info):
            schema = runnertype_parameter_info[name]
        if 'template' in node:
            render_context[name] = env.from_string(node['template']).render(render_context)
        if 'value' in node:
            render_context[name] = node['value']
        if name in render_context:
            render_context[name] = _cast(render_context[name], schema)

    runner_params, action_params = _split_params(runnertype_parameter_info, action_parameter_info,
                                                 render_context)

    return (runner_params, action_params)


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
