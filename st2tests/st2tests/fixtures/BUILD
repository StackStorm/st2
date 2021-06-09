resources(
    # used by tests in st2-rbac-backend
    name="rbac_fixtures",
    sources=[
        "./rbac/**/*.yaml",
        "./rbac_invalid/**/*.yaml",
    ],
)

# Please make sure to register all of the packs in this dir.
# For each pack, depend on the python_sources target (which depends on pack_metadata).
target(
    name="child_packs",
    dependencies=[
        "./aliases",
        "./backstop",
        "./descendants",
        "./generic",
        "./localrunner_pack",
        "./rule_enforcements",
        "./timers",
        "./traces",
    ],
)
