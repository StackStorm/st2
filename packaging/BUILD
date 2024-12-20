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

# Relevant nFPM docs:
# - https://www.pantsbuild.org/stable/reference/targets/nfpm_deb_package
# - https://www.pantsbuild.org/stable/reference/targets/nfpm_rpm_package
# - arch: https://nfpm.goreleaser.com/goarch-to-pkg/

_pkg_description = """
StackStorm Event-driven automation
Package is full standalone st2 installation including all components
in a pre-built venv.
"""
_common_pkg_metadata = dict(
    package_name="st2",
    description=_pkg_description,
    homepage="https://stackstorm.com",
    license="Apache-2.0",
    version="",  # TODO: where does version come from?
    # arch used to be "any", but that was not correct as the venv has compiled packages.
    arch="amd64",  # TODO: parametrize this?
    platform="linux",
)
_maintainer = "StackStorm Engineering <opsadmin@stackstorm.com>"  # TODO: update this

nfpm_deb_package(
    name="st2.deb",
    maintainer=_maintainer,
    fields={
        # https://www.debian.org/doc/debian-policy/ch-controlfields.html#source
        # "Source": "st2",  # TODO: do we really have an "st2" source package?
        # https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-vcs-fields
        "Vcs-Git": "git://github.com/stackstorm/st2.git",
        "Vcs-Browser": "https://github.com/stackstorm/st2",
    },
    section="python",
    priority="optional",
    **_common_pkg_metadata,
)

nfpm_rpm_package(
    name="st2.rpm",
    vendor="The StackStorm Project",
    packager=_maintainer,
    # group="System/Management",  # was only useful for EL 5 and earlier
    compression="zstd:default",  # EL 9
    # compression="xz",  # EL 8
    **_common_pkg_metadata,
)
