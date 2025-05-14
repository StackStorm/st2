__defaults__(all=dict(inject_pack_python_path=True))

pack_metadata(
    name="metadata",
)

python_requirements(
    name="reqs",
)

st2_pack_archive(
    dependencies=[
        ":metadata",
        ":reqs",
        "./actions",
        "./actions/checks",
        # "./actions/lib",  # nothing in dir
        "./sensors",
        "./tests",
    ],
)
