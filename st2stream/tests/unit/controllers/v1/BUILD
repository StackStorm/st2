python_tests(
    name="tests",
    stevedore_namespaces=[
        "st2common.rbac.backend",
        "st2common.runners.runner",
        "st2common.metrics.driver",
    ],
    uses=["mongo"],
)

python_test_utils(
    sources=["*.py", "!test_*.py"],
)
