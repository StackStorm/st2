file(
    name="logging_console",
    source="console.conf",
)

files(
    name="logging",
    sources=["logging*.conf"],
    overrides={
        "logging.conf": {
            "dependencies": [
                "//:reqs#python-json-logger",
            ],
        },
    },
)

files(
    name="logging_syslog",
    sources=["syslog*.conf"],
)
