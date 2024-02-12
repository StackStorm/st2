# rules on what st2client can depend on
__dependencies_rules__(
    (
        # All sources in st2client
        "*",
        (
            # may depend on 3rd party dependencies,
            "//reqs#*",
            # and on anything in this diretory,
            "/**",
            # but nothing else (eg not st2common, st2*, runners, ...).
            "!*",
        ),
    ),
)

python_sources()
