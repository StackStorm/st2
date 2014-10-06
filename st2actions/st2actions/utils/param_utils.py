import ast
import copy
import json
import six

from jinja2 import Template, Environment, StrictUndefined, meta
from st2common import log as logging
from st2common.exceptions import actionrunner


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
            if key == 'immutable':
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

    required = set((getattr(runner_db, 'required_parameters', list()) +
                    getattr(action_db, 'required_parameters', list())))

    def is_immutable(param_meta):
        return param_meta.get('immutable', False)

    immutable = {param for param in parameters if is_immutable(merged_params.get(param))}
    required = required - immutable
    optional = parameters - required - immutable

    required_params = {k: merged_params[k] for k in required}
    optional_params = {k: merged_params[k] for k in optional}
    immutable_params = {k: merged_params[k] for k in immutable}

    return (required_params, optional_params, immutable_params)


def _split_params(runner_parameters, action_parameters, mixed_params):
    pf = lambda params: {k: v for k, v in six.iteritems(mixed_params) if k in params}
    return (pf(runner_parameters), pf(action_parameters))


def _get_resolved_runner_params(runner_parameters, action_parameters,
                                actionexec_runner_parameters):
    # Runner parameters should use the defaults from the RunnerType object.
    # The runner parameter defaults may be overridden by values provided in
    # the Action and ActionExecution.

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
        if param_name in action_parameters and 'default' in action_parameters[param_name]:
            action_param = action_parameters[param_name]
            resolved_params[param_name] = action_param['default']
            # No further override if param is immutable
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


def get_resolved_params(runnertype_parameter_info, action_parameter_info, actionexec_parameters):
    # Runner parameters should use the defaults from the RunnerType object.
    # The runner parameter defaults may be overridden by values provided in
    # the Action and ActionExecution.
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
    template = Template(template_str)
    return template_str != template.render({})


def _renderable_context_param_split(action_parameters, runner_parameters):
    # To render the params it is necessary to combine the params together so that cross
    # parameter category references are resolved.
    renderable_params = {}
    context_params = {}

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
    while len(renderable_params) != 0:
        for k, v in six.iteritems(renderable_params):
            template = env.from_string(v)
            try:
                rendered = template.render(rendered_params)
                rendered_params[k] = rendered
            except:
                LOG.debug('Failed to render %s: %s', k, v, exc_info=True)
        for k in rendered_params:
            if k in renderable_params:
                del renderable_params[k]
    return rendered_params


def _cast_params(rendered, parameter_schemas):
    casts = {
        'array': (lambda x: json.loads(x) if isinstance(x, str) or isinstance(x, unicode)
                  else x),
        'boolean': (lambda x: ast.literal_eval(x.capitalize())
                    if isinstance(x, str) or isinstance(x, unicode) else x),
        'integer': int,
        'number': float,
        'object': (lambda x: json.loads(x) if isinstance(x, str) or isinstance(x, unicode)
                   else x),
        'string': str
    }
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
        cast = casts.get(parameter_type, None)
        if not cast:
            continue
        casted_params[k] = cast(v)
    return casted_params


def get_rendered_params(runner_parameters, action_parameters, runnertype_parameter_info,
                        action_parameter_info):
    '''
    Renders the templates in runner_parameters and action_parameters. Using the type information
    from *_parameter_info will appropriately cast the parameters.
    '''
    # To render the params it is necessary to combine the params together so that cross
    # parameter category references are resolved.
    renderable_params, context = _renderable_context_param_split(action_parameters,
                                                                 runner_parameters)
    rendered_params = _do_render_params(renderable_params, context)
    template_free_params = {}
    template_free_params.update(rendered_params)
    template_free_params.update(context)

    r_runner_parameters, r_action_parameters = _split_params(runnertype_parameter_info,
                                                             action_parameter_info,
                                                             template_free_params)

    return (_cast_params(r_runner_parameters, runnertype_parameter_info),
            _cast_params(r_action_parameters, action_parameter_info))


def get_finalized_params(runnertype_parameter_info, action_parameter_info, actionexec_parameters):
    '''
    Finalize the parameters for an action to execute by doing the following -
        1. Split the parameters into those consumed by runner and action into separate dicts.
        2. Render any templates in the parameters.
    '''
    runner_params, action_params = get_resolved_params(runnertype_parameter_info,
                                                       action_parameter_info,
                                                       actionexec_parameters)
    runner_params, action_params = get_rendered_params(runner_params, action_params,
                                                       runnertype_parameter_info,
                                                       action_parameter_info)
    return (runner_params, action_params)
