__dependents_rules__(
    (
        # graphviz and pika
        (
            {"path": "/", "name": "graphviz"},
            {"path": "/", "name": "pika"},
        ),
        # can used by tools in this directory
        "/**",
        # and nothing else
        "!*",
    ),
    # everything else is not restricted
    ("*", "*"),
)

python_requirement(
    name="graphviz",
    requirements=["graphviz"],
    # used by st2-analyze-links.py and visualize_action_chain.py
)

python_requirement(
    name="pika",
    requirements=["pika"],
    # used by direct_queue_publisher.py
)

python_sources(
    overrides={
        "config_gen.py": dict(
            dependencies=[
                # the auth backends get listed in the conf file
                "//:auth_backends",
                # We are using string import detection to gather the imports
                # from CONFIGS in config_gen.py. The following command is
                # helpful in validating that dependencies include everything:
                # grep -rl '^def register_opts(ignore_errors=False):' st2*
            ]
        ),
    },
)

shell_sources(
    name="shell",
    sources=[
        "*.sh",
        "st2-setup-*",
    ],
    skip_shellcheck=True,
    dependencies=[
        "conf:st2_dev_conf",
    ],
)
