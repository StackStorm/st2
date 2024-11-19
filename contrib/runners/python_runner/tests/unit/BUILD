__defaults__(
    {python_test: dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    overrides={
        "test_output_schema.py": dict(
            dependencies=[
                "st2tests/st2tests/resources/packs/pythonactions/actions/pascal_row.py",
                "//:capture_git_modules",
            ],
        ),
        "test_pythonrunner.py": dict(
            dependencies=[
                "st2tests/st2tests/resources/packs/pythonactions/actions",
                "//:capture_git_modules",
            ],
            stevedore_namespaces=[
                "st2common.metrics.driver",
                "st2common.rbac.backend",
            ],
        ),
    },
)
