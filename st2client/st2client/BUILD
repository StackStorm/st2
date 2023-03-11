__dependencies_rules__(
    (
        # All sources in st2client
        "*",
        # may depend on 3rd party dependencies,
        {"path": "//", "name": "reqs#*"},
        # and on anything in this diretory,
        "/**",
        # but nothing else (eg not st2common, st2*, runners, ...).
        "!*",
    ),
)

python_sources()
