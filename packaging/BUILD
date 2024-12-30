python_sources()

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
    version="",  # TODO: where does version come from?
    # arch used to be "any", but that was not correct as the venv has compiled packages.
    arch="amd64",  # TODO: parametrize this?
    platform="linux",
)
_maintainer = "StackStorm Engineering <opsadmin@stackstorm.com>"  # TODO: update this

nfpm_deb_package(
    name="st2.deb",
    dependencies=[
        "./deb/scripts",
        "./deb/systemd:services",
        "./common/systemd:generators",
        ":st2_venv@parametrize=py38",
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
        # "Source": "st2",  # TODO: do we really have an "st2" source package?
        # https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-vcs-fields
        "Vcs-Git": "git://github.com/stackstorm/st2.git",
        "Vcs-Browser": "https://github.com/stackstorm/st2",
    },
    section="python",
    priority="optional",
    # package relationships
    predepends=[
        "dpkg (>= 1.16.16)",
        # "${pre:Depends}",
        "python3 (>= 3.8)",
        # "${misc:Pre-Depends}",
        "adduser",
    ],
    depends=[
        "sudo",
        "adduser",
        "libssl-dev",
        "libffi-dev",
        "git",
        "libpam0g",
        "openssh-server",
        "openssh-client",
        "bash",
        "netbase",
        # "${Depends}",
        "python3-distutils",
        "python3-dev",
        # We use nFPM, not debhelpers, so these do not make sense:
        # "${shlibs:Depends}",  # We explicitly disabled the analogous RPM feature
        # "libc6 (>= 2.29)",
        # "libexpat1 (>= 2.1~beta3)",
        # "libgcc-s1 (>= 4.2)",
        # "libldap-2.4-2 (>= 2.4.11)",
        # "libstdc++6 (>= 5.2)",
        # "zlib1g (>= 1:1.2.0)",
        # "${misc:Depends}",
    ],
    conflicts=[
        "st2common",
    ],
    **_common_pkg_metadata,
)

nfpm_rpm_package(
    name="st2.rpm",
    dependencies=[
        "./rpm/scripts",
        "./rpm/systemd:services",
        "./common/systemd:generators",
        ":st2_venv@parametrize=py38",
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
    compression="zstd:default",  # EL 9
    # compression="xz",  # EL 8
    # package relationships
    depends=[  # aka Requires
        "openssl-devel",
        "libffi-devel",
        "git",
        "pam",
        "openssh-server",
        "openssh-clients",
        "bash",
        "setup",
        # TODO: parametrize
        "python3-devel",  # EL 8
        "python38-devel",  # EL 9
        # These are in the native built rpms (this list is deduplicated)
        # "/bin/bash",
        # "/bin/sh",
        # "/opt/stackstorm/st2/bin/python",
        # "/usr/bin/env",
        # "config(st2) = 3.9dev-80",  # provided by this package
        # "ld-linux-x86-64.so.2()(64bit)",
        # "ld-linux-x86-64.so.2(GLIBC_2.3)(64bit)",
        # "libc.so.6()(64bit)",
        # "libc.so.6(GLIBC_2.12)(64bit)",
        # "libc.so.6(GLIBC_2.14)(64bit)",
        # "libc.so.6(GLIBC_2.17)(64bit)",
        # "libc.so.6(GLIBC_2.18)(64bit)",
        # "libc.so.6(GLIBC_2.2.5)(64bit)",
        # "libc.so.6(GLIBC_2.25)(64bit)",
        # "libc.so.6(GLIBC_2.28)(64bit)",
        # "libc.so.6(GLIBC_2.3)(64bit)",
        # "libc.so.6(GLIBC_2.3.4)(64bit)",
        # "libc.so.6(GLIBC_2.4)(64bit)",
        # "libc.so.6(GLIBC_2.6)(64bit)",
        # "libc.so.6(GLIBC_2.7)(64bit)",
        # "libdl.so.2()(64bit)",
        # "libdl.so.2(GLIBC_2.2.5)(64bit)",
        # "libffi-devel",
        # "libgcc_s.so.1()(64bit)",
        # "libgcc_s.so.1(GCC_3.0)(64bit)",
        # "libgcc_s.so.1(GCC_3.3)(64bit)",
        # "libgcc_s.so.1(GCC_4.2.0)(64bit)",
        # "liblber.so.2()(64bit)",
        # "liblber.so.2(OPENLDAP_2.200)(64bit)",
        # "libldap.so.2()(64bit)",
        # "libldap.so.2(OPENLDAP_2.200)(64bit)",
        # "libm.so.6()(64bit)",
        # "libpthread.so.0()(64bit)",
        # "libpthread.so.0(GLIBC_2.2.5)(64bit)",
        # "libpthread.so.0(GLIBC_2.3.2)(64bit)",
        # "libstdc++.so.6()(64bit)",
        # "libstdc++.so.6(CXXABI_1.3)(64bit)",
        # "libstdc++.so.6(CXXABI_1.3.7)(64bit)",
        # "libstdc++.so.6(CXXABI_1.3.9)(64bit)",
        # "libstdc++.so.6(GLIBCXX_3.4)(64bit)",
        # "libstdc++.so.6(GLIBCXX_3.4.11)(64bit)",
        # "libstdc++.so.6(GLIBCXX_3.4.21)(64bit)",
        # "rpmlib(CompressedFileNames) = 3.0.4-1",
        # "rpmlib(FileDigests) = 4.6.0-1",
        # "rpmlib(PayloadFilesHavePrefix) = 4.0-1",
        # "rpmlib(PayloadIsZstd) = 5.4.18-1",
        # "rtld(GNU_HASH)",
    ],
    conflicts=[
        "st2common",
    ],
    # TODO: Does nFPM auto generate any provides entries?
    # provides=[
    #     # These are in the native built rpms
    #     "config(st2)",
    #     "st2",
    #     "st2(x86-64)",
    # ],
    **_common_pkg_metadata,
)
