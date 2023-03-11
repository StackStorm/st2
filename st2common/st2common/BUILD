__dependencies_rules__(
    (
        # All sources in st2common
        "*",
        # may depend on 3rd party dependencies,
        {"path": "//", "name": "reqs#*"},
        # and on st2client
        "//st2client/st2client/**",
        # and on anything in this diretory,
        "/**",
        # but nothing else (eg not st2common, st2*, runners, ...).
        "!*",
    ),
)

__dependents_rules__(
    # All sources in st2common may be a dependency of anything except st2client
    ("*", "!//st2client/**", "*"),
)

python_sources(
    dependencies=[
        ":openapi_spec",
    ]
)

# These may be loaded with st2common.util.spec_loader
resource(
    name="openapi_spec_template",
    source="openapi.yaml.j2",
)
api_spec(
    name="openapi_spec",
    source="openapi.yaml",
    dependencies=[
        ":openapi_spec_template",
        "st2common/st2common/cmd/generate_api_spec.py",  # st2-generate-api-spec
        "st2common/st2common/cmd/validate_api_spec.py",  # st2-validate-api-spec
        "//conf:st2_dev_conf",  # used for both generate and validate
    ],
)
