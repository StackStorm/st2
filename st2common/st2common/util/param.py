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

import re
import six
import networkx as nx

from jinja2 import meta, exceptions
from oslo_config import cfg
from st2common import log as logging
from st2common.util.config_loader import get_config
from st2common.util.jinja import is_jinja_expression
from st2common.constants.action import ACTION_CONTEXT_KV_PREFIX
from st2common.constants.pack import PACK_CONFIG_CONTEXT_KV_PREFIX
from st2common.constants.keyvalue import (
    DATASTORE_PARENT_SCOPE,
    SYSTEM_SCOPE,
    FULL_SYSTEM_SCOPE,
)
from st2common.constants.keyvalue import USER_SCOPE, FULL_USER_SCOPE
from st2common.exceptions.param import ParamException
from st2common.services.keyvalues import KeyValueLookup, UserKeyValueLookup
from st2common.util.casts import get_cast
from st2common.util.compat import to_unicode
from st2common.util import jinja as jinja_utils
from st2common.util.jsonify import json_encode
from st2common.util.jsonify import json_decode


LOG = logging.getLogger(__name__)
ENV = jinja_utils.get_jinja_environment()

__all__ = [
    "render_live_params",
    "render_final_params",
]


def _split_params(runner_parameters, action_parameters, mixed_params):
    def pf(params, skips):
        result = {
            k: v
            for k, v in six.iteritems(mixed_params)
            if k in params and k not in skips
        }
        return result

    return (pf(runner_parameters, {}), pf(action_parameters, runner_parameters))


def _cast_params(rendered, parameter_schemas):
    """
    It's just here to make tests happy
    """
    casted_params = {}
    for k, v in six.iteritems(rendered):
        casted_params[k] = _cast(v, parameter_schemas[k] or {})
    return casted_params


def _cast(v, parameter_schema):
    if v is None or not parameter_schema:
        return v

    parameter_type = parameter_schema.get("type", None)
    if not parameter_type:
        return v

    cast = get_cast(cast_type=parameter_type)
    if not cast:
        return v

    return cast(v)


def _create_graph(action_context, config):
    """
    Creates a generic directed graph for depencency tree and fills it with basic context variables
    """
    G = nx.DiGraph()
    system_keyvalue_context = {
        SYSTEM_SCOPE: KeyValueLookup(scope=FULL_SYSTEM_SCOPE, context=action_context)
    }

    # If both 'user' and 'api_user' are specified, this prioritize 'api_user'
    user = action_context["user"] if "user" in action_context else None
    user = action_context["api_user"] if "api_user" in action_context else user

    if not user:
        # When no user is not specified, this selects system-user's scope by default.
        user = cfg.CONF.system_user.user
        LOG.info(
            "Unable to retrieve user / api_user value from action_context. Falling back "
            "to and using system_user (%s)." % (user)
        )

    system_keyvalue_context[USER_SCOPE] = UserKeyValueLookup(
        scope=FULL_USER_SCOPE, user=user, context=action_context
    )
    G.add_node(DATASTORE_PARENT_SCOPE, value=system_keyvalue_context)
    G.add_node(ACTION_CONTEXT_KV_PREFIX, value=action_context)
    G.add_node(PACK_CONFIG_CONTEXT_KV_PREFIX, value=config)
    return G


def _process(G, name, value):
    """
    Determines whether parameter is a template or a value. Adds graph nodes and edges accordingly.
    """
    # Jinja defaults to ascii parser in python 2.x unless you set utf-8 support on per module level
    # Instead we're just assuming every string to be a unicode string
    if isinstance(value, str):
        value = to_unicode(value)

    complex_value_str = None
    if isinstance(value, list) or isinstance(value, dict):
        complex_value_str = str(value)

    is_jinja_expr = jinja_utils.is_jinja_expression(
        value
    ) or jinja_utils.is_jinja_expression(complex_value_str)

    if is_jinja_expr:
        try:
            template_ast = ENV.parse(value)
            G.add_node(name, template=value)

            LOG.debug("Template ast: %s", template_ast)
            # Dependencies of the node represent jinja variables used in the template
            # We're connecting nodes with an edge for every depencency to traverse them
            # in the right order and also make sure that we don't have missing or cyclic
            # dependencies upfront.
            dependencies = meta.find_undeclared_variables(template_ast)
            LOG.debug("Dependencies: %s", dependencies)
            if dependencies:
                for dependency in dependencies:
                    G.add_edge(dependency, name)
        except exceptions.TemplateSyntaxError:
            G.add_node(name, value=value)
            # not jinja after all
            # is_jinga_expression only checks for {{ or {{% for speed
    else:
        G.add_node(name, value=value)


def _process_defaults(G, schemas):
    """
    Process dependencies for parameters default values in the order schemas are defined.
    """
    for schema in schemas:
        for name, value in six.iteritems(schema):
            absent = name not in G.nodes
            is_none = G.nodes.get(name, {}).get("value") is None
            immutable = value.get("immutable", False)
            if absent or is_none or immutable:
                _process(G, name, value.get("default"))


def _validate(G):
    """
    Validates dependency graph to ensure it has no missing or cyclic dependencies
    """
    for name in G.nodes:
        if "value" not in G.nodes[name] and "template" not in G.nodes[name]:
            msg = 'Dependency unsatisfied in variable "%s"' % name
            raise ParamException(msg)

    if not nx.is_directed_acyclic_graph(G):
        graph_cycles = nx.simple_cycles(G)

        variable_names = []
        for cycle in graph_cycles:
            try:
                variable_name = cycle[0]
            except IndexError:
                continue

            variable_names.append(variable_name)

        variable_names = ", ".join(sorted(variable_names))
        msg = (
            "Cyclic dependency found in the following variables: %s. Likely the variable is "
            "referencing itself" % (variable_names)
        )
        raise ParamException(msg)


def _render(node, render_context):
    """
    Render the node depending on its type
    """
    if "template" in node:
        complex_type = False

        if isinstance(node["template"], list) or isinstance(node["template"], dict):
            node["template"] = json_encode(node["template"])

            # Finds occurrences of "{{variable}}" and adds `to_complex` filter
            # so types are honored. If it doesn't follow that syntax then it's
            # rendered as a string.
            node["template"] = re.sub(
                r'"{{([A-z0-9_-]+)}}"', r"{{\1 | to_complex}}", node["template"]
            )
            LOG.debug("Rendering complex type: %s", node["template"])
            complex_type = True

        LOG.debug("Rendering node: %s with context: %s", node, render_context)

        result = ENV.from_string(str(node["template"])).render(render_context)

        LOG.debug("Render complete: %s", result)

        if complex_type:
            result = json_decode(result)
            LOG.debug("Complex Type Rendered: %s", result)

        return result
    if "value" in node:
        return node["value"]


def _resolve_dependencies(G):
    """
    Traverse the dependency graph starting from resolved nodes
    """
    context = {}
    for name in nx.topological_sort(G):
        node = G.nodes[name]
        try:
            context[name] = _render(node, context)

        except Exception as e:
            LOG.debug("Failed to render %s: %s", name, e, exc_info=True)
            msg = 'Failed to render parameter "%s": %s' % (name, six.text_type(e))
            raise ParamException(msg)

    return context


def _cast_params_from(params, context, schemas):
    """
    Pick a list of parameters from context and cast each of them according to the schemas provided
    """
    result = {}

    # First, cast only explicitly provided live parameters
    for name in params:
        param_schema = {}
        for schema in schemas:
            if name in schema:
                param_schema = schema[name]
        result[name] = _cast(context[name], param_schema)

    # Now, iterate over all parameters, and add any to the live set that satisfy ALL of the
    # following criteria:
    #
    # - Have a default value that is a Jinja template
    # - Are using the default value (i.e. not being overwritten by an actual live param)
    #
    # We do this because the execution API controller first determines live params before
    # validating params against the schema. So, we want to make sure that if the default
    # value is a template, it is rendered and added to the live params before this validation.
    for schema in schemas:
        for param_name, param_details in schema.items():

            # Skip if the parameter have immutable set to true in schema
            if param_details.get("immutable"):
                continue

            # Skip if the parameter doesn't have a default, or if the
            # value in the context is identical to the default
            if (
                "default" not in param_details
                or param_details.get("default") == context[param_name]
            ):
                continue

            # Skip if the default value isn't a Jinja expression
            if not is_jinja_expression(param_details.get("default")):
                continue

            # Skip if the parameter is being overridden
            if param_name in params:
                continue

            result[param_name] = _cast(context[param_name], param_details)

    return result


def render_live_params(
    runner_parameters,
    action_parameters,
    params,
    action_context,
    additional_contexts=None,
):
    """
    Renders list of parameters. Ensures that there's no cyclic or missing dependencies. Returns a
    dict of plain rendered parameters.
    """
    additional_contexts = additional_contexts or {}

    pack = action_context.get("pack")
    user = action_context.get("user")

    try:
        config = get_config(pack, user)
    except Exception as e:
        LOG.info(
            "Failed to retrieve config for pack %s and user %s: %s"
            % (pack, user, six.text_type(e))
        )
        config = {}

    G = _create_graph(action_context, config)

    # Additional contexts are applied after all other contexts (see _create_graph), but before any
    # of the dependencies have been resolved.
    for name, value in six.iteritems(additional_contexts):
        G.add_node(name, value=value)

    [_process(G, name, value) for name, value in six.iteritems(params)]
    _process_defaults(G, [action_parameters, runner_parameters])
    _validate(G)

    context = _resolve_dependencies(G)
    live_params = _cast_params_from(
        params, context, [action_parameters, runner_parameters]
    )

    return live_params


def render_final_params(runner_parameters, action_parameters, params, action_context):
    """
    Renders missing parameters required for action to execute. Treats parameters from the dict as
    plain values instead of trying to render them again. Returns dicts for action and runner
    parameters.
    """
    config = get_config(action_context.get("pack"), action_context.get("user"))

    G = _create_graph(action_context, config)

    # by that point, all params should already be resolved so any template should be treated value
    [G.add_node(name, value=value) for name, value in six.iteritems(params)]
    _process_defaults(G, [action_parameters, runner_parameters])
    _validate(G)

    context = _resolve_dependencies(G)
    context = _cast_params_from(
        context, context, [action_parameters, runner_parameters]
    )

    return _split_params(runner_parameters, action_parameters, context)


def get_finalized_params(
    runnertype_parameter_info,
    action_parameter_info,
    liveaction_parameters,
    action_context,
):
    """
    Left here to keep tests running. Later we would need to split tests so they start testing each
    function separately.
    """
    params = render_live_params(
        runnertype_parameter_info,
        action_parameter_info,
        liveaction_parameters,
        action_context,
    )
    return render_final_params(
        runnertype_parameter_info, action_parameter_info, params, action_context
    )
