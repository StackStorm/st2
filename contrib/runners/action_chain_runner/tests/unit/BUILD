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
    # TODO: need st2common.runners.runner stevedore namespace, but only this runner!
    #dependencies=[
    #    "contrib/runners/action_chain_runner",
    #],
)
