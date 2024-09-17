__defaults__(
    {python_test: dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    overrides={
        (
            "test_execution_cancellation.py",
            "test_runner_container.py",
            "test_worker.py",
        ): dict(
            uses=["system_user"],
        ),
    },
)
