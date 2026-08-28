__defaults__(
    {python_test: dict(tags=["integration"])},
    extend=True,
)

python_tests(
    name="tests",
    overrides={
        "test_localrunner.py": dict(
            stevedore_namespaces=[
                "st2common.metrics.driver",
            ],
        ),
    },
)