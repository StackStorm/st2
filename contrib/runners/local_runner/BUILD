st2_runner_python_distribution(
    runner_name="local",
    description=(
        "Local Shell Command and Script action runner "
        "for the StackStorm event-driven automation platform"
    ),
    entry_points={
        stevedore_namespace("st2common.runners.runner"): {
            "local-shell-cmd": "local_runner.local_shell_command_runner",
            "local-shell-script": "local_runner.local_shell_script_runner",
        },
    },
)
