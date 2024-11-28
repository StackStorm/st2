__defaults__(
    {python_test: dict(tags=["integration"])},
    extend=True,
)

python_tests(
    name="tests",
    stevedore_namespaces=[
        "orquesta.expressions.functions",
        "st2common.runners.runner",
        "st2common.rbac.backend",
        "st2common.metrics.driver",
    ],
    uses=["mongo", "rabbitmq", "redis"],
    overrides={
        "test_logging.py": dict(
            dependencies=[
                "./log_unicode_data.py",
            ],
        ),
        "test_register_content_script.py": dict(
            dependencies=[
                "conf/st2.tests.conf:st2_tests_conf",
                "conf/st2.tests1.conf:st2_tests_conf",
                "st2common/bin/st2-register-content",
            ],
        ),
        "test_service_setup_log_level_filtering.py": dict(
            dependencies=[
                "st2api/bin/st2api",
            ],
        ),
        "test_util_green.py": dict(
            dependencies=[
                "st2common/tests/fixtures/print_to_stdout_stderr_sleep.sh:shell_resources",
            ],
        ),
    },
)

python_test_utils(
    sources=["*.py", "!test_*.py"],
    overrides={
        "log_unicode_data.py": dict(
            dependencies=[
                "st2tests/st2tests/fixtures/conf:st2.tests.conf",
            ],
        ),
    },
)
