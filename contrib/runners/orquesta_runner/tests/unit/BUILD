__defaults__(
    {(python_test, python_tests): dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    dependencies=[
        # most files import tests.unit.base which is ambiguous. Tell pants which one to use.
        "contrib/runners/orquesta_runner/tests/unit/base.py",
    ],
)

python_test_utils(
    sources=["*.py", "!test_*.py"],
)
