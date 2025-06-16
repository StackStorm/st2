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

from dataclasses import dataclass
from typing import Any, Optional

import requests
from pants.engine.env_vars import EnvironmentVars, EnvironmentVarsRequest
from requests.auth import HTTPBasicAuth

from pants.engine.internals.selectors import Get
from pants.engine.rules import _uncacheable_rule, collect_rules

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


@dataclass(frozen=True)
class PackageCloudNextReleaseRequest:
    nfpm_arch: str
    distro_id: str
    package_name: str
    package_version: str
    production: bool


@dataclass(frozen=True)
class PackageCloudNextRelease:
    value: Optional[int] = None


@_uncacheable_rule
async def packagecloud_get_next_release(
    request: PackageCloudNextReleaseRequest,
) -> PackageCloudNextRelease:
    env_vars: EnvironmentVars = await Get(
        EnvironmentVars, EnvironmentVarsRequest(["PACKAGECLOUD_TOKEN"])
    )
    package_cloud_token = env_vars.get("PACKAGECLOUD_TOKEN")
    if not package_cloud_token:
        return PackageCloudNextRelease()

    client = requests.session()
    client.auth = HTTPBasicAuth(package_cloud_token, "")

    def get(url_path: str) -> list[dict[str, Any]]:
        response = client.get(f"https://packagecloud.io{url_path}")
        response.raise_for_status()
        ret: list[dict[str, Any]] = response.json()
        next_url = response.links.get("next", {}).get("url")
        while next_url:
            response = client.get(f"https://packagecloud.io{next_url}")
            response.raise_for_status()
            ret.extend(response.json())
            next_url = response.links.get("next", {}).get("url")
        return ret

    distro_id = request.distro_id
    distro_info = DISTRO_INFO[distro_id]
    pkg_is_unstable = "dev" in request.package_version

    # packagecloud url params:
    org = "stackstorm"
    repo = f"{'' if request.production else 'staging-'}{'unstable' if pkg_is_unstable else 'stable'}"
    pkg_type = distro_info["pkg_type"]
    distro = distro_info["distro"]
    distro_version = distro_id if pkg_type == "deb" else distro_info["version"]
    pkg_name = request.package_name
    arch = ARCH_NAMES[request.nfpm_arch][pkg_type]

    # https://packagecloud.io/docs/api#resource_packages_method_index (api doc incorrectly drops /:package)
    # /api/v1/repos/:user_id/:repo/packages/:type/:distro/:version/:package/:arch.json
    index_url = f"/api/v1/repos/{org}/{repo}/packages/{pkg_type}/{distro}/{distro_version}/{pkg_name}/{arch}.json"
    package_index: list[dict[str, Any]] = get(index_url)
    if not package_index:
        return PackageCloudNextRelease()

    versions_url: str = package_index[0]["versions_url"]
    versions: list[dict[str, Any]] = get(versions_url)
    releases = [
        version_info["release"]
        for version_info in versions
        if version_info["version"] == request.package_version
    ]
    if not releases:
        return PackageCloudNextRelease()

    max_release = max(int(release) for release in releases)
    next_release = max_release + 1
    return PackageCloudNextRelease(next_release)


def rules():
    return [
        *collect_rules(),
    ]
