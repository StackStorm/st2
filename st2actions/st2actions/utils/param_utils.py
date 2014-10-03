import copy


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

    return required_params, optional_params, immutable_params
