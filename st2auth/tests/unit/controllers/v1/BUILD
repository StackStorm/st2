python_tests(
    name="tests",
    dependencies=[
        # most files import tests.base which is ambiguous. Tell pants which one to use.
        "st2auth/tests/base.py",
    ],
)
