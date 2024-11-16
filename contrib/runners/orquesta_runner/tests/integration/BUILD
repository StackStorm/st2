__defaults__(
    {python_test: dict(tags=["integration"])},
    extend=True,
)

python_tests(
    name="tests",
    uses=["mongo", "rabbitmq", "redis", "system_user"],
)
