python_sources(
    sources=["*.py", "st2*", "!st2ctl", "!st2-self-check", "!st2-run-pack-tests"],
    skip_flake8=True,
    # skip until resolved: https://github.com/PyCQA/pylint/issues/2095
    skip_pylint=True,
)

# TODO: consider adding pex_binary targets for the st2-* python scripts.
# Normally, pex tries to import scripts that it runs, but the python import system does
# not allow scripts to include the "-" character in their filename.
# With pantsbuild 2.20+, we can set the pex_binary(executable=) field which makes pex
# read the script's contents instead of attempting to import it.

st2_shell_sources_and_resources(
    name="shell",
    sources=["st2ctl", "st2-self-check", "st2-run-pack-tests"],
    skip_shellcheck=True,
    overrides={
        "st2ctl": dict(
            dependencies=[
                "./st2-register-content",
                "./st2-cleanup-db",
            ],
        ),
        "st2-self-check": dict(
            dependencies=[
                "./st2ctl:shell",
                # TODO: dep on st2client cli?
            ],
        ),
        # st2-run-pack-tests creates its own virtualenv on the fly and
        # installs its dependencies, so most don't need to be listed here.
        # It can optionally use the deps installed with st2tests package.
        "st2-run-pack-tests": dict(
            dependencies=[
                "//:reqs#virtualenv",
                "//:reqs#pip",
                "//:reqs#setuptools",
                "//:reqs#wheel",
            ],
        ),
    },
)
