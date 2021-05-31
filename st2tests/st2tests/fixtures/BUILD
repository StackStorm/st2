resources(
    # used by tests in st2-rbac-backend
    name="rbac_fixtures",
    sources=[
        "./rbac/**/*.yaml",
        "./rbac_invalid/**/*.yaml",
    ],
)

target(
    name="packs_metadata",
    dependencies=[
        "./aliases:metadata",
        "./backstop:metadata",
        "./generic:metadata",
        "./localrunner_pack:metadata",
        "./packs:packs_metadata",
        "./packs_1:packs_metadata",
        "./packs_invalid:packs_metadata",
        "./traces:metadata",
    ],
)
