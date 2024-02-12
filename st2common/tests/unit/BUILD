__defaults__(
    {(python_test, python_tests): dict(tags=["unit"])},
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
    uses=["mongo", "rabbitmq"],
    overrides={
        "test_util_file_system.py": dict(
            dependencies=[
                "st2tests/st2tests/policies",
                "st2tests/st2tests/policies/meta",
            ],
        ),
    },
)

python_test_utils(
    sources=["*.py", "!test_*.py"],
)
