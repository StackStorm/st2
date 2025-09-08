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
    # https://jfearn.fedorapeople.org/en-US/RPM/4/html-single/RPM_Guide/index.html#idp3030720
    license="Apache-2.0",  # TODO: nFPM is putting this under Copyright tag instead of License
    version="",  # injected by pants-plugins/release
    # arch used to be "any", but that was not correct as the venv has compiled packages.
    arch="amd64",  # NOTE: parametrize this if adding support for arm64 or other arch.
    platform="linux",
)
_maintainer = "StackStorm Engineering <opsadmin@stackstorm.com>"  # TODO: update this


def _st2_venv_deps() -> list[str]:
    """Return a list of deps required to build the st2 venv.

    The :st2_venv parametrizations depend on parametrizations of :st2.pex,
    so, make sure to keep these 3 lists of parametrizations in sync.
    """
    return [f":st2_venv@parametrize=py3{m}" for m in ("8", "9", "10", "11")]


def _distro(distro_id: str, **kwargs):
    return parametrize(
        distro_id,
        distro_id=distro_id,
        **kwargs,
    )


nfpm_deb_package(
    name="st2.deb",
    dependencies=[
        "./deb/scripts",
        "./deb/systemd:services",
        "./common/systemd:generators",
        "./common:conf_files",
        "./common:dirs",
        "./common:symlinks",
        *_st2_venv_deps(),
        ":default_packs",
        ":extra_packs",
    ],
    scripts=dict(
        preinstall="deb/scripts/pre-install.sh",
        postinstall="deb/scripts/post-install.sh",
        preremove="deb/scripts/pre-remove.sh",
        postremove="deb/scripts/post-remove.sh",
        # config="",
        # templates="",
        # rules="",
    ),
    maintainer=_maintainer,
    fields={
        # https://www.debian.org/doc/debian-policy/ch-controlfields.html#source
        # We do not have an "st2" source package, so do not include "Source".
        # https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-vcs-fields
        "Vcs-Git": "git://github.com/stackstorm/st2.git",
        "Vcs-Browser": "https://github.com/stackstorm/st2",
    },
    section="python",
    priority="optional",
    **_common_pkg_metadata,
    **_distro("focal"),
)

nfpm_rpm_package(
    name="st2.rpm",
    dependencies=[
        "./rpm/scripts",
        "./rpm/systemd:services",
        "./common/systemd:generators",
        "./common:conf_files",
        "./common:dirs",
        "./common:symlinks",
        *_st2_venv_deps(),
        ":default_packs",
        ":extra_packs",
    ],
    ghost_contents=[
        "/opt/stackstorm/install/st2.pex",  # a symlink (default in post-install; users may modify)
    ],
    scripts=dict(
        preinstall="rpm/scripts/pre-install.sh",
        postinstall="rpm/scripts/post-install.sh",
        preremove="rpm/scripts/pre-remove.sh",
        postremove="rpm/scripts/post-remove.sh",
        # pretrans="",
        # posttrans="",
        # verify="",
    ),
    vendor="The StackStorm Project",
    packager=_maintainer,
    # group="System/Management",  # was only useful for EL 5 and earlier
    compression="zstd:best",  # xz and lzma are ~3x slower than gzip or zstd
    **_common_pkg_metadata,
    **_distro("el8"),
    **_distro("el9"),
)
