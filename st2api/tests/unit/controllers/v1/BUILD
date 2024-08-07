python_tests(
    name="tests",
    stevedore_namespaces=[
        "st2common.runners.runner",
        "st2common.rbac.backend",
        "st2common.metrics.driver",
    ],
    uses=["mongo"],
    overrides={
        "test_webhooks.py": dict(
            dependencies=[
                "st2common/st2common/models/api/webhook.py",
            ],
        ),
    },
)
