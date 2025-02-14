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
        "test_packs.py": dict(
            # use the fixture to resolve ambiguous import (ambiguous due to symlink of core pack)
            dependencies=[
                "st2tests/st2tests/fixtures/packs/core/actions/inject_trigger.py"
            ],
        ),
    },
)
