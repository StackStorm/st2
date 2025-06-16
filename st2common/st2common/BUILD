_ST2COMMON_DEPENDENCIES_RULE = (
    # All selected code (see the actual rule):
    # may depend on 3rd party dependencies
    "//reqs#*",
    # and on st2client
    "//st2client/st2client/**",
    # and on packs, runners, etc
    "//contrib/**",
    # and on conf files
    "//conf/**",
    # and on anything in this directory,
    "/**",
    # but nothing else (eg not st2api, st2auth, tools, ...)
    "!*",
)

# rules on what st2commonn can depend on
__dependencies_rules__(
    (
        # Only the inquiry service
        "/services/inquiry.py",
        # may depend on st2actions.containers.base ('?' makes this a WARNING),
        (
            # TODO: refactor inquiry.py to not import from st2actions
            "?//st2actions/st2actions/container/base.py",
        ),
        # and may depend on code according to these rules.
        _ST2COMMON_DEPENDENCIES_RULE,
    ),
    (
        # All remaining sources in st2common
        "*",
        # may depend on code according to these rules
        _ST2COMMON_DEPENDENCIES_RULE,
    ),
)

# rules on what can depend on st2commonn
__dependents_rules__(
    # All sources in st2common may be a dependency of anything except st2client
    ("*", "!//st2client/st2client/**", "*"),
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
