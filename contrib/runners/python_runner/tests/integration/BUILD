__defaults__(
    {python_test: dict(tags=["integration"])},
    extend=True,
)

python_tests(
    name="tests",
    overrides={
        "test_python_action_process_wrapper.py": dict(
            dependencies=["contrib/examples/actions/noop.py"]
        )
    },
)
