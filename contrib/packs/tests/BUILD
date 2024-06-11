# tests can only be dependencies of other tests in this directory
__dependents_rules__(("*", "/**", "!*"))

__defaults__(
    {(python_test, python_tests): dict(tags=["unit", "pack"])},
    extend=True,
)

python_tests(
    skip_pylint=True,
)
