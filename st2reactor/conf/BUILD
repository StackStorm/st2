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

st2_logging_conf_for_nfpm(
    dependencies=[
        ":logging",
        ":logging_syslog",
    ],
    files=[
        ("logging.garbagecollector.conf", "/etc/st2/logging.garbagecollector.conf"),
        ("syslog.garbagecollector.conf", "/etc/st2/syslog.garbagecollector.conf"),
        ("logging.rulesengine.conf", "/etc/st2/logging.rulesengine.conf"),
        ("syslog.rulesengine.conf", "/etc/st2/syslog.rulesengine.conf"),
        ("logging.sensorcontainer.conf", "/etc/st2/logging.sensorcontainer.conf"),
        ("syslog.sensorcontainer.conf", "/etc/st2/syslog.sensorcontainer.conf"),
        ("logging.timersengine.conf", "/etc/st2/logging.timersengine.conf"),
        ("syslog.timersengine.conf", "/etc/st2/syslog.timersengine.conf"),
    ],
)
