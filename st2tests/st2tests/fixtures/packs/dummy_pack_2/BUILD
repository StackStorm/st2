pack_metadata(
    name="metadata",
)

resource(
    name="pack_requirements",
    source="requirements.txt",
)

python_sources(
    dependencies=[
        ":metadata",
        "./actions",
        "./sensors",
    ],
)
