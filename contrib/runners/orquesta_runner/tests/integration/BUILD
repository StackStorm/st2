__defaults__(
    {python_test: dict(tags=["integration"])},
    extend=True,
)

python_tests(
    name="tests",
    uses=["mongo", "rabbitmq", "redis", "st2cluster", "system_user"],
    tags=["integration", "st2cluster"],
)
