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

# The st2-packages repo installed this separately to avoid relying on setup.py.
# With the move to pants+pex managed virtualenv, the setup.py issue is (probably) not an issue.
# If that assumption proves wrong, use something like this to install it:
# nfpm_content_file(
#     name="runners_sh",
#     src="runners.sh",
#     dst="/opt/stackstorm/st2/bin/runners.sh"
#     file_owner="root",
#     file_group="root",
#     file_mode="rwxr-xr-x",
# )
