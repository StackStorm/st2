file(
    name="apache_sample_conf",
    source="apache.sample.conf",
)

file(
    name="htpasswd",
    source="htpasswd_dev",
)

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
