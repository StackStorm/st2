st2_runner_python_distribution(
    runner_name="orquesta",
    description=(
        "Orquesta workflow runner "
        "for the StackStorm event-driven automation platform"
    ),
    entry_points={
        stevedore_namespace("st2common.runners.runner"): {
            "orquesta": "orquesta_runner.orquesta_runner",
        },
        stevedore_namespace("orquesta.expressions.functions"): {
            "st2kv": "orquesta_functions.st2kv:st2kv_",
            "task": "orquesta_functions.runtime:task",
            "basename": "st2common.expressions.functions.path:basename",
            "dirname": "st2common.expressions.functions.path:dirname",
            "from_json_string": "st2common.expressions.functions.data:from_json_string",
            "from_yaml_string": "st2common.expressions.functions.data:from_yaml_string",
            "json_dump": "st2common.expressions.functions.data:to_json_string",
            "json_parse": "st2common.expressions.functions.data:from_json_string",
            "json_escape": "st2common.expressions.functions.data:json_escape",
            "jsonpath_query": "st2common.expressions.functions.data:jsonpath_query",
            "regex_match": "st2common.expressions.functions.regex:regex_match",
            "regex_replace": "st2common.expressions.functions.regex:regex_replace",
            "regex_search": "st2common.expressions.functions.regex:regex_search",
            "regex_substring": "st2common.expressions.functions.regex:regex_substring",
            "to_human_time_from_seconds": "st2common.expressions.functions.time:to_human_time_from_seconds",
            "to_json_string": "st2common.expressions.functions.data:to_json_string",
            "to_yaml_string": "st2common.expressions.functions.data:to_yaml_string",
            "use_none": "st2common.expressions.functions.data:use_none",
            "version_compare": "st2common.expressions.functions.version:version_compare",
            "version_more_than": "st2common.expressions.functions.version:version_more_than",
            "version_less_than": "st2common.expressions.functions.version:version_less_than",
            "version_equal": "st2common.expressions.functions.version:version_equal",
            "version_match": "st2common.expressions.functions.version:version_match",
            "version_bump_major": "st2common.expressions.functions.version:version_bump_major",
            "version_bump_minor": "st2common.expressions.functions.version:version_bump_minor",
            "version_bump_patch": "st2common.expressions.functions.version:version_bump_patch",
            "version_strip_patch": "st2common.expressions.functions.version:version_strip_patch",
            "yaml_dump": "st2common.expressions.functions.data:to_yaml_string",
            "yaml_parse": "st2common.expressions.functions.data:from_yaml_string",
        },
    },
)
