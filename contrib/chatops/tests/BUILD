files(
    name="fixtures",
    sources=["fixtures/*.json"],
)

python_tests(
    name="tests",
    dependencies=[":fixtures"],
    skip_pylint=True,
)
