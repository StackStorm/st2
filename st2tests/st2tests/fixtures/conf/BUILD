resources(
    name="st2.tests.conf",
    sources=["st2.tests*.conf"],
    dependencies=["st2tests/conf:other-logging-conf"],
)

files(
    name="logging-conf",
    sources=["logging.*.conf"],
)

python_sources(
    dependencies=[
        ":st2.tests.conf",
    ],
)
