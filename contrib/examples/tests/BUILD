# tests can only be dependencies of other tests in this directory
__dependents_rules__(("*", "/**", f"//{build_file_dir().parent}:files", "!*"))

__defaults__(
    {python_test: dict(tags=["pack"])},
    extend=True,
)

python_tests(
    skip_pylint=True,
)
