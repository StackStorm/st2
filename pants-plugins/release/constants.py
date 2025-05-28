# Copyright 2025 The StackStorm Authors.
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

from __future__ import annotations

ARCH_NAMES = {  # {nfpm_arch: {pkg_type: packagecloud_arch}}
    # The key comes from the 'arch' field of nfpm_*_package targets (GOARCH or GOARCH+GOARM).
    #   https://www.pantsbuild.org/stable/reference/targets/nfpm_deb_package#arch
    #   https://www.pantsbuild.org/stable/reference/targets/nfpm_rpm_package#arch
    "amd64": {
        "deb": "amd64",
        "rpm": "x86_64",
    }
}

# This includes distros we do not support.
DISTROS_BY_PKG_TYPE = {  # {pkg_type: {distro: {distro_id: distro_version}}}
    "deb": {
        "debian": {  # no releases in packagecloud (so far)
            "buster": "10",
            "bullseye": "11",
            "bookworm": "12",
            "trixie": "13",
            "forky": "14",
        },
        "ubuntu": {  # Only LTS releases
            "trusty": "14.04",  # the oldest with releases in packagecloud
            "xenial": "16.04",
            "bionic": "18.04",
            "focal": "20.04",
            "jammy": "22.04",
            "noble": "24.04",
        },
    },
    "rpm": {
        "el": {  # EL = Enterprise Linux (RHEL, Rocky, Alma, ...)
            # 6 is the oldest with releases in packagecloud
            f"el{v}": f"{v}"
            for v in (6, 7, 8, 9)
        },
    },
}

DISTRO_INFO = {
    distro_id: {
        "distro": distro,
        "version": distro_version,
        "pkg_type": pkg_type,
    }
    for pkg_type, distros in DISTROS_BY_PKG_TYPE.items()
    for distro, distro_ids in distros.items()
    for distro_id, distro_version in distro_ids.items()
}

DISTRO_PACKAGE_SEARCH_URL = {
    "debian": "https://packages.debian.org/search",
    "ubuntu": "https://packages.ubuntu.com/search",
}
