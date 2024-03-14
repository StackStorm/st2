__dependents_rules__(
    (
        # winrm
        {"path": "/", "name": "winrm"},
        # can ONLY be used by sources in the winrm_runner
        "/**",
        # and nothing else
        "!*",
    ),
    # everything else is not restricted
    ("*", "*"),
)

python_requirement(
    name="winrm",
    requirements=["pywinrm"],
    # modules can be removed once pants is released with
    # https://github.com/pantsbuild/pants/pull/17390
    modules=["winrm"],
)

st2_runner_python_distribution(
    runner_name="winrm",
    description=(
        "WinRM shell command and PowerShell command and script action runner "
        "for the StackStorm event-driven automation platform"
    ),
    entry_points={
        stevedore_namespace("st2common.runners.runner"): {
            "winrm-cmd": "winrm_runner.winrm_command_runner",
            "winrm-ps-cmd": "winrm_runner.winrm_ps_command_runner",
            "winrm-ps-script": "winrm_runner.winrm_ps_script_runner",
        },
    },
)
