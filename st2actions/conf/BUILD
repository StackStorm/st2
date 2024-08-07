st2_logging_conf_file(
    name="logging_console",
    source="console.conf",
)

st2_logging_conf_files(
    name="logging",
    sources=["logging*.conf"],
    dependencies=["//:logs_directory"],
    overrides={
        "logging.conf": dict(
            dependencies=[
                "//:logs_directory",
                "//:reqs#python-json-logger",
            ],
        ),
    },
)

st2_logging_conf_files(
    name="logging_syslog",
    sources=["syslog*.conf"],
)
