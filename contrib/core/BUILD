__defaults__(all=dict(inject_pack_python_path=True))

pack_metadata(
    name="metadata",
)

python_requirements(
    name="reqs",
    source="requirements-tests.txt",
)

python_sources(
    # this is for fixture.py
    dependencies=[
        ":metadata",
        "./actions",
        "./actions/send_mail:send_mail_resources",
    ],
)

st2_pack_archive(
    dependencies=[
        ":metadata",
        ":reqs",
        "./actions",
        "./actions/send_mail:send_mail_resources",
        "./tests",
    ],
)
