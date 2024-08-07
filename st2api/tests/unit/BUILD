__defaults__(
    {python_test: dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    dependencies=["//:rbac_backends"],
    stevedore_namespaces=[
        "st2common.rbac.backend",
    ],
    uses=["mongo"],
)
