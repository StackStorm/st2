pack_metadata(
    name="metadata",
    dependencies=[":pack_requirements"],
)

resource(
    name="pack_requirements",
    source="requirements.txt",
)

python_sources(
    dependencies=[":metadata"],
)
