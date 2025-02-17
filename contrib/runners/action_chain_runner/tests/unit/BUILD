__defaults__(
    {python_test: dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    stevedore_namespaces=[
        "st2common.rbac.backend",
        "st2common.metrics.driver",
        # the core pack uses all runners.
        "st2common.runners.runner",
    ],
    uses=["mongo"],
)
