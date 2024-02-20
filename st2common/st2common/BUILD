_ST2COMMON_DEPENDENCIES_RULE = (
    # st2common can only depend on:
    "//st2common/**",  # st2common itself
    "//contrib/**",  # packs, runners, etc.
    "//st2client/st2client/**",
    "//reqs#*",
    "//conf/**",
    # Prohibit st2common from depending on any st2* libs except st2common and st2client.
    "!//st2*/st2*/**",
    # Prohibit dependencies on any other python_sources in the repo
    "!<python_source*>",
    # Prohibt dependencies on anything else
    "!*",
)

# rules on what st2commonn can depend on
__dependencies_rules__(
    (  # The exception rule set
        "/services/inquiry.py",  # only apply exception to inquiry.py
        (
            # WARN (The '?') about importing st2actions.container.base
            # TODO: refactor inquiry.py to not import from st2actions
            "?//st2actions/st2actions/container/base.py",
        ),
        _ST2COMMON_DEPENDENCIES_RULE,
    ),
    (  # The catch-all rule set
        "*",  # Apply rules to all st2common targets
        _ST2COMMON_DEPENDENCIES_RULE,
    ),
)

# rules on what can depend on st2commonn
__dependents_rules__(
    (
        "*",  # Apply rules to all st2common targets
        (
            # prohibit st2client from depending on st2common
            "!//st2client/st2client/**",
            # allow everything else to depend on st2common
            "*",
        ),
    ),
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
