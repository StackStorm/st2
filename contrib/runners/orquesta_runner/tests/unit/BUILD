__defaults__(
    {python_test: dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    stevedore_namespaces=[
        "st2common.metrics.driver",
        "st2common.rbac.backend",
        # the core pack uses all runners.
        "st2common.runners.runner",
        "orquesta.expressions.functions",
    ],
    overrides={
        "test_policies.py": dict(
            dependencies=["st2actions/st2actions/policies/retry.py"]
        )
    }
)

python_test_utils(
    sources=["*.py", "!test_*.py"],
)
