__defaults__(
    {python_test: dict(tags=["unit"])},
    extend=True,
)

python_tests(
    name="tests",
    stevedore_namespaces=[
        "st2common.rbac.backend",
        "st2common.metrics.driver",
        # TODO: we only need THIS runner, but this pulls in all.
        "st2common.runners.runner",
    ],
    uses=["mongo"],
    # TODO: this will allow us to depend only on this runner once we upgrade to pants 2.23
    #       https://github.com/pantsbuild/pants/pull/21062
    #entry_point_dependencies={
    #    "contrib/runners/action_chain_runner": ["st2common.runners.runner"],
    #},
)
