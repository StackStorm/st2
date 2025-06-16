__defaults__(
    {python_test: dict(tags=["integration"])},
    extend=True,
)

python_tests(
    name="tests",
    uses=["rabbitmq"],
    stevedore_namespaces=[
        "st2common.metrics.driver",
    ],
)
