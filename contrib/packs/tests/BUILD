# tests can only be dependencies of other tests in this directory
__dependents_rules__(("*", "/**", "!*"))

__defaults__(
    {python_test: dict(tags=["pack"])},
    extend=True,
)

python_tests(
    skip_pylint=True,
    overrides={
        "test_action_aliases.py": dict(
            dependencies=[
                # test needs the pack and aliases metadata
                "contrib/packs:metadata",
            ],
        ),
        "test_action_unload.py": dict(
            stevedore_namespaces=[
                "st2common.metrics.driver",
            ],
            entry_point_dependencies={
                "contrib/runners/http_runner": ["st2common.runners.runner"],
                "contrib/runners/local_runner": ["st2common.runners.runner"],
                "contrib/runners/python_runner": ["st2common.runners.runner"],
            },
        ),
    },
)
