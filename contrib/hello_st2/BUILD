__defaults__(all=dict(inject_pack_python_path=True))

pack_metadata(
    name="metadata",
)

# Capture the requirements file for distribution in the pack archive;
# we do not need to use `python_requirements()` for this sample file.
files(
    name="reqs",
    sources=["requirements*.txt"],
)

st2_pack_archive(
    dependencies=[
        ":metadata",
        ":reqs",
        "./actions",
        "./sensors",
    ],
)
