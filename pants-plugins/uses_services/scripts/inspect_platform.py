# Copyright 2023 The StackStorm Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json

from dataclasses import asdict, dataclass

__all__ = ["Platform"]


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


def _get_platform() -> Platform:
    # late import so that Platform can be imported in the pants plugin as well
    import distro
    import platform

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


if __name__ == "__main__":
    platform = _get_platform()
    platform_dict = asdict(platform)
    print(json.dumps(platform_dict))
