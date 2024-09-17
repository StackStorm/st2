python_tests(
    name="tests",
    overrides={
        (
            "test_alias_execution.py",
            "test_auth.py",
            "test_auth_api_keys.py",
            "test_executions.py",
            "test_inquiries.py",
        ): dict(
            uses=["system_user"],
        ),
    },
)
