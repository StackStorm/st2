# rules on what st2client can depend on
__dependencies_rules__(
    (
        "*",  # Apply rules to all st2client targets
        (
            # st2client can only depend on:
            "//st2client/**",  # st2client itself
            "//reqs#*",  # 3rd party deps
            # st2client cannot depend on any other modules in this repo.
            "!*",
        ),
    ),
)

python_sources()
