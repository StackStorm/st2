import platform
from dataclasses import dataclass

import distro

from pants.engine.rules import collect_rules, _uncacheable_rule


@dataclass(frozen=True)
class Platform:
    arch: str
    os: str
    distro: str
    distro_name: str
    distro_codename: str
    distro_like: str
    distro_major_version: str
    distro_version: str
    mac_release: str
    win_release: str


@_uncacheable_rule
async def get_platform() -> Platform:
    return Platform(
        arch=platform.machine(),  # x86_64
        os=platform.system(),  # Linux, Darwin
        distro=distro.id(),  # rhel, ubuntu, centos, gentoo, darwin
        distro_name=distro.name(),  # Ubuntu, Centos Linux, Gentoo, Darwin
        distro_codename=distro.codename(),  # xenial, Core, n/a, ''
        distro_like=distro.like(),  # debian, rhel fedora, '', ''
        distro_major_version=distro.major_version(),  # 16, 7, 2, 19
        distro_version=distro.version(),  # 16.04, 7, 2.7, 19.6.0
        mac_release=platform.mac_ver()[0],  # '', 10.15.7
        win_release=platform.win32_ver()[0],  # ''
    )


def rules():
    return collect_rules()
