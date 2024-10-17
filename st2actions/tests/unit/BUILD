__defaults__(
    {python_test: dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    uses=["mongo"],
    overrides={
        (
            "test_execution_cancellation.py",
            "test_runner_container.py",
            "test_worker.py",
        ): dict(
            uses=["mongo", "system_user"],
        ),
        (
            "test_execution*.py",
            "test_notifier.py",
            "test_output_schema.py",
            "test_policies.py",
            "test_queue_consumers.py",
            "test_runner_container.py",
            "test_scheduler*.py",
            "test_worker.py",
            "test_workflow_engine.py",
        ): dict(
            stevedore_namespaces=[
                "st2common.runners.runner",
                "st2common.metrics.driver",
            ],
        ),
    },
)
