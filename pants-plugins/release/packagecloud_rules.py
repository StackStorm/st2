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

import aiohttp
from pants.engine.env_vars import EnvironmentVars, EnvironmentVarsRequest

from pants.engine.internals.selectors import Get
from pants.engine.rules import _uncacheable_rule, collect_rules

from .constants import ARCH_NAMES, DISTRO_INFO


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

    http_auth = aiohttp.HTTPBasicAuth(package_cloud_token, "")

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

    async with aiohttp.ClientSession(auth=http_auth) as client:
        package_index: list[dict[str, Any]] = await get(client, index_url)
        if not package_index:
            return PackageCloudNextRelease()

        versions_url: str = package_index[0]["versions_url"]
        versions: list[dict[str, Any]] = await get(client, versions_url)

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


async def get(client: aiohttp.ClientSession, url_path: str) -> list[dict[str, Any]]:
    """Get packagecloud URL, handling any results paging."""
    async with client.get(
        f"https://packagecloud.io{url_path}", raise_for_status=True
    ) as response:
        ret: list[dict[str, Any]] = await response.json()
        next_url = response.links.get("next", {}).get("url")
    while next_url:
        async with client.get(
            f"https://packagecloud.io{next_url}", raise_for_status=True
        ) as response:
            ret.extend(await response.json())
            next_url = response.links.get("next", {}).get("url")
    return ret


def rules():
    return [
        *collect_rules(),
    ]
