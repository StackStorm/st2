__defaults__(
    {(python_test, python_tests): dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    dependencies=[
        # several files import tests.unit.base which is ambiguous. Tell pants which one to use.
        "st2common/tests/unit/base.py",
    ],
    uses=["mongo"],
)

python_sources()
