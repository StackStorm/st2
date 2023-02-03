st2_runner_python_distribution(
    runner_name="remote",
    description=(
        "Remote SSH shell command and script action runner "
        "for the StackStorm event-driven automation platform"
    ),
    entry_points={
        stevedore_namespace("st2common.runners.runner"): {
            "remote-shell-cmd": "remote_runner.remote_command_runner",
            "remote-shell-script": "remote_runner.remote_script_runner",
        },
    },
)
