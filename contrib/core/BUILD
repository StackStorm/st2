__defaults__(all=dict(inject_pack_python_path=True))

pack_metadata(
    name="metadata",
)

python_requirements(
    name="reqs",
    source="requirements-tests.txt",
)

python_sources(
    dependencies=[
        ":metadata",
        "./actions",
        "./actions/send_mail:send_mail_resources",
    ],
)
