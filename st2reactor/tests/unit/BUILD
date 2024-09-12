__defaults__(
    {python_test: dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    uses=["mongo"],
    overrides={
        "test_enforce.py": dict(
            stevedore_namespaces=[
                "st2common.rbac.backend",
                "st2common.runners.runner",
                "st2common.metrics.driver",
            ],
        ),
        "test_rule_engine.py": dict(
            stevedore_namespaces=[
                "st2common.runners.runner",
                "st2common.metrics.driver",
            ],
        ),
    },
)
