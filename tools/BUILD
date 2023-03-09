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
        "config_gen.py": {
            "dependencies": [
                # the auth backends get listed in the conf file
                "//:auth_backends",
                # the following should match CONFIGS in config_gen.py
                # grep -rl '^def register_opts(ignore_errors=False):' st2*
                "st2actions/st2actions/scheduler/config.py",
                "st2actions/st2actions/workflows/config.py",
                "st2actions/st2actions/notifier/config.py",
                "st2actions/st2actions/config.py",
                "st2api/st2api/config.py",
                "st2auth/st2auth/config.py",
                "st2common/st2common/config.py",
                "st2reactor/st2reactor/garbage_collector/config.py",
                "st2reactor/st2reactor/timer/config.py",
                "st2reactor/st2reactor/sensor/config.py",
                "st2reactor/st2reactor/rules/config.py",
                "st2stream/st2stream/config.py",
            ]
        },
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
