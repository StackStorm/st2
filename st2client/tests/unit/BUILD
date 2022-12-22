__defaults__(
    {(python_test, python_tests): dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    dependencies=[
        "st2client/tests/fixtures:st2client_ini",
        # most files import tests.base which is ambiguous. Tell pants which one to use.
        "st2client/tests/base.py",
    ],
)
