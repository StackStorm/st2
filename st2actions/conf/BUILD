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

st2_logging_conf_for_nfpm(
    dependencies=[
        ":logging",
        ":logging_syslog",
    ],
    files=[
        ("logging.conf", "/etc/st2/logging.actionrunner.conf"),
        ("syslog.conf", "/etc/st2/syslog.actionrunner.conf"),
        ("logging.notifier.conf", "/etc/st2/logging.notifier.conf"),
        ("syslog.notifier.conf", "/etc/st2/syslog.notifier.conf"),
        ("logging.scheduler.conf", "/etc/st2/logging.scheduler.conf"),
        ("syslog.scheduler.conf", "/etc/st2/syslog.scheduler.conf"),
        ("logging.workflowengine.conf", "/etc/st2/logging.workflowengine.conf"),
        ("syslog.workflowengine.conf", "/etc/st2/syslog.workflowengine.conf"),
    ],
)
