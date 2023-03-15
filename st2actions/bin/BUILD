python_sources(
    sources=["st2*"],
    skip_flake8=True,
    # skip until resolved: https://github.com/PyCQA/pylint/issues/2095
    skip_pylint=True,
)

st2_shell_sources_and_resources(
    name="shell",
    sources=["*.sh"],
    skip_shellcheck=True,
)
