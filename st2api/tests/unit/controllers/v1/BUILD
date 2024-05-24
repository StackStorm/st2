python_tests(
    name="tests",
    stevedore_namespaces=[
        "st2common.runners.runner",
        "st2common.rbac.backend",
        "st2common.metrics.driver",
    ],
    uses=["mongo"],
    overrides={
        (
            "test_alias_execution.py",
            "test_auth.py",
            "test_auth_api_keys.py",
            "test_executions.py",
            "test_inquiries.py",
        ): dict(
            uses=["mongo", "system_user"],
        ),
        "test_webhooks.py": dict(
            dependencies=[
                "st2common/st2common/models/api/webhook.py",
            ],
        ),
    },
)
