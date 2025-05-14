__defaults__(
    {python_test: dict(tags=["integration"])},
    extend=True,
)

python_tests(
    name="tests",
    dependencies=[
        "conf/st2.tests.conf:st2_tests_conf",
        "st2api/st2api/wsgi.py",
        "st2auth/st2auth/wsgi.py",
    ],
    stevedore_namespaces=[
        "st2auth.sso.backends",
        "st2common.metrics.driver",
        "st2common.rbac.backend",
    ],
    uses=["mongo", "rabbitmq", "redis"],
)
