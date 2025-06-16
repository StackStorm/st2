__defaults__(all=dict(inject_pack_python_path=True))

pack_metadata(
    name="metadata",
)

st2_pack_archive(
    dependencies=[
        ":metadata",
        "./actions",
        "./actions/pack_mgmt",
        "./tests",
    ],
)
