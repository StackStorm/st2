# tests can only be dependencies of other tests in this directory
__dependents_rules__(("*", "/**", "!*"))

__defaults__(
    {python_test: dict(tags=["pack"])},
    extend=True,
)

files(
    name="fixtures",
    sources=["fixtures/*.json"],
)

python_tests(
    name="tests",
    dependencies=[
        ":fixtures",
        "contrib/chatops:metadata",
    ],
    skip_pylint=True,
)
