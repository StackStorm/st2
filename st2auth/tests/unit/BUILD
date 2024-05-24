__defaults__(
    {(python_test, python_tests): dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    dependencies=["//:auth_backends"],
    uses=["mongo"],
)
