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
            "test_actions.py",
            "test_action_alias.py",
            "test_executions_filters.py",
            "test_kvps.py",
            "test_packs.py",
            "test_rules.py",
            "test_sensortypes.py",
            "test_triggers.py",
            "test_triggertypes.py",
            "test_triggerinstances.py",
        ): dict(
            uses=["mongo", "rabbitmq", "redis"],
        ),
        ("test_alias_execution.py", "test_executions.py", "test_inquiries.py"): dict(
            uses=["mongo", "rabbitmq", "redis", "system_user"],
        ),
        "test_service_registry.py": dict(
            uses=["mongo", "redis"],
        ),
        ("test_auth.py", "test_auth_api_keys.py"): dict(
            uses=["mongo", "system_user"],
        ),
        "test_webhooks.py": dict(
            dependencies=[
                "st2common/st2common/models/api/webhook.py",
            ],
        ),
    },
)
