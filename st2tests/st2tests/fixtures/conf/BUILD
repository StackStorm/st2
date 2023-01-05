resources(
    name="st2.tests.conf",
    sources=[
        "st2.tests*.conf",
        "logging.*.conf",  # used by st2.tests*.conf
    ],
    dependencies=[
        "st2tests/conf:other_logging_conf",
        # depending on st2auth from st2tests is not nice.
        "st2auth/conf:htpasswd",
    ],
)

python_sources(
    dependencies=[
        ":st2.tests.conf",
    ],
)
