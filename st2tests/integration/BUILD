__defaults__(
    {python_test: dict(tags=["integration"])},
    all=dict(
        skip_pylint=True,
    ),
)

shell_sources(
    name="shell",
    dependencies=[
        "st2tests/conf:st2.conf",
        "st2tests/conf:vagrant_ssh_key",
    ],
    skip_shellcheck=True,
)
