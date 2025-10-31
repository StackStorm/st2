__defaults__(
    {python_test: dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    dependencies=["//:auth_backends"],
    uses=["mongo"],
)
