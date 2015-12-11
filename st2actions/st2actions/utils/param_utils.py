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
import networkx as nx

from jinja2 import Environment, StrictUndefined, meta
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


def process(G, name, value):
    env = Environment(undefined=StrictUndefined)
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

def render_live_params(runnertype_parameter_info, action_parameter_info, liveaction_parameters,
                       action_context):
    '''
    This function would happen on a st2api side and would only apply to manual action invocations
    and calls from mistral
    '''
    render_context = {}
    env = Environment(undefined=StrictUndefined)

    G = nx.DiGraph()
    G.add_node(SYSTEM_KV_PREFIX, value=KeyValueLookup())
    G.add_node(ACTION_CONTEXT_KV_PREFIX, value=action_context)

    for name, value in six.iteritems(liveaction_parameters):
        process(G, name, value)

    for name, value in six.iteritems(runnertype_parameter_info):
        if 'default' in value and name not in liveaction_parameters or value.get('immutable', False):
            process(G, name, value['default'])

    for name, value in six.iteritems(action_parameter_info):
        if 'default' in value and name not in liveaction_parameters or value.get('immutable', False):
            process(G, name, value['default'])

    for name in G.nodes():
        if 'value' not in G.node[name] and 'template' not in G.node[name]:
            msg = 'Dependecy unsatisfied in %s' % name
            raise actionrunner.ActionRunnerException(msg)

    if not nx.is_directed_acyclic_graph(G):
        msg = 'Cyclic dependecy found'
        raise actionrunner.ActionRunnerException(msg)

    for name in nx.topological_sort(G):
        node = G.node[name]
        if 'template' in node:
            try:
                render_context[name] = env.from_string(node['template']).render(render_context)
            except Exception as e:
                LOG.debug('Failed to render %s: %s', name, e, exc_info=True)
                msg = 'Failed to render parameter "%s": %s' % (name, str(e))
                raise actionrunner.ActionRunnerException(msg)
        if 'value' in node:
            render_context[name] = node['value']

    params = {}
    for name in liveaction_parameters:
        schema = {}
        if (name in action_parameter_info):
            schema = action_parameter_info[name]
        if (name in runnertype_parameter_info):
            schema = runnertype_parameter_info[name]
        params[name] = _cast(render_context[name], schema)

    return params


def render_final_params(runnertype_parameter_info, action_parameter_info, liveaction_parameters,
                        action_context):
    '''
    This one would later became `get_finalized_params` and will be handling both calls from api and
    those that came from action_chain and rule engine.
    '''
    render_context = {}
    env = Environment(undefined=StrictUndefined)

    G = nx.DiGraph()
    G.add_node(SYSTEM_KV_PREFIX, value=KeyValueLookup())
    G.add_node(ACTION_CONTEXT_KV_PREFIX, value=action_context)

    params = copy.copy(liveaction_parameters)

    for name, value in six.iteritems(params):
        process(G, name, value)

    for name, value in six.iteritems(runnertype_parameter_info):
        if 'default' in value and name not in params or value.get('immutable', False):
            process(G, name, value['default'])

    for name, value in six.iteritems(action_parameter_info):
        if 'default' in value and name not in params or value.get('immutable', False):
            process(G, name, value['default'])

    if not nx.is_directed_acyclic_graph(G):
        msg = 'Cyclic dependecy found'
        raise actionrunner.ActionRunnerException(msg)

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

    runner_params, action_params = _split_params(runnertype_parameter_info, action_parameter_info, render_context)

    return (runner_params, action_params)


def get_finalized_params(runnertype_parameter_info, action_parameter_info, liveaction_parameters,
                         action_context):
    '''
    I'm leaving both functions in the same file for now just to keep tests intact, make sure I
    haven't messed up the logic and to make it easier for you to understand what's happening there.
    '''

    params = render_live_params(runnertype_parameter_info, action_parameter_info,
                                liveaction_parameters, action_context)
    return render_final_params(runnertype_parameter_info, action_parameter_info, params,
                               action_context)
