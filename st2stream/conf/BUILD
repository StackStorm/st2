st2_logging_conf_file(
    name="logging_console",
    source="console.conf",
)

st2_logging_conf_file(
    name="logging",
    source="logging.conf",
    dependencies=["//:logs_directory"],
)

st2_logging_conf_file(
    name="logging_gunicorn",
    source="logging.gunicorn.conf",
    dependencies=["//:logs_directory"],
)

st2_logging_conf_file(
    name="logging_syslog",
    source="syslog.conf",
)

st2_logging_conf_for_nfpm(
    dependencies=[
        ":logging",
        ":logging_gunicorn",
        ":logging_syslog",
    ],
    files=[
        ("logging.conf", "/etc/st2/logging.stream.conf"),
        ("logging.gunicorn.conf", "/etc/st2/logging.stream.gunicorn.conf"),
        ("syslog.conf", "/etc/st2/syslog.stream.conf"),
    ],
)
