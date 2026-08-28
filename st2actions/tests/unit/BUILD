__defaults__(
    {python_test: dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    uses=["mongo"],
    stevedore_namespaces=[
        "st2common.runners.runner",
        "st2common.metrics.driver",
    ],
    overrides={
        (
            "test_executions.py",
            "test_policies.py",
            "test_scheduler.py",
            "test_workflow_engine.py",
        ): dict(
            uses=["mongo", "rabbitmq", "redis"],
        ),
        ("test_execution_cancellation.py", "test_worker.py"): dict(
            uses=["mongo", "rabbitmq", "redis", "system_user"],
        ),
        "test_runner_container.py": dict(
            uses=["mongo", "system_user"],
        ),
    },
)
