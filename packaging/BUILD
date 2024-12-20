# We use st2-py*.pex to quickly build a venv (like /opt/stackstorm/st2)
# that includes all requirements and our wheels.
pex_binary(
    name="st2.pex",
    dependencies=[
        # this should depend on all python_distribution targets
        "//st2actions",
        "//st2api",
        "//st2auth",
        "//st2client",
        "//st2common",
        "//st2reactor",
        "//st2stream",
        "//st2tests",
        "//contrib/runners/action_chain_runner",
        "//contrib/runners/announcement_runner",
        "//contrib/runners/http_runner",
        "//contrib/runners/inquirer_runner",
        "//contrib/runners/local_runner",
        "//contrib/runners/noop_runner",
        "//contrib/runners/orquesta_runner",
        "//contrib/runners/python_runner",
        "//contrib/runners/remote_runner",
        "//contrib/runners/winrm_runner",
    ],
    include_tools=True,  # include pex.tools to populate a venv from the pex
    include_sources=False,  # always includes generated wheels, so transitive sources not needed
    venv_hermetic_scripts=False,  # do not add -sE to script shebangs
    # 1 parametrize group per python minor version in [DEFAULT].st2_interpreter_constraints in pants.toml
    **parametrize(
        "py38",
        output_path="st2-py38.pex",
        interpreter_constraints=["CPython==3.8.*"],
    ),
    **parametrize(
        "py39",
        output_path="st2-py39.pex",
        interpreter_constraints=["CPython==3.9.*"],
    ),
    **parametrize(
        "py310",
        output_path="st2-py310.pex",
        interpreter_constraints=["CPython==3.10.*"],
    ),
    **parametrize(
        "py311",
        output_path="st2-py311.pex",
        interpreter_constraints=["CPython==3.11.*"],
    ),
)
