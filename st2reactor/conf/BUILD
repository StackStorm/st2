st2_logging_conf_file(
    name="logging_console",
    source="console.conf",
)

st2_logging_conf_files(
    name="logging",
    sources=["logging*.conf"],
    dependencies=["//:logs_directory"],
)

st2_logging_conf_files(
    name="logging_syslog",
    sources=["syslog*.conf"],
)
