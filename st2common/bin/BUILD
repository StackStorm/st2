python_sources(
    sources=["*.py", "st2*", "!st2ctl", "!st2-self-check", "!st2-run-pack-tests"],
    skip_flake8=True,
)

shell_sources(
    name="shell",
    sources=["st2ctl", "st2-self-check", "st2-run-pack-tests"],
    skip_shellcheck=True,
)
