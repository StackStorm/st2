python_tests(
    name="tests",
    uses=["mongo", "rabbitmq", "redis", "st2cluster", "system_user"],
    tags=["integration", "st2cluster"],
)

python_test_utils(
    sources=["*.py", "!test_*.py"],
)
