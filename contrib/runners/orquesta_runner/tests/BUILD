__defaults__(
    all=dict(
        skip_pylint=True,
        entry_point_dependencies={
            "contrib/runners/orquesta_runner": [
                "st2common.runners.runner",
                "orquesta.expressions.functions",
            ],
        },
    )
)

# tests can only be dependencies of other tests in this directory
__dependents_rules__(("*", "/**", "!*"))
