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

from collections import defaultdict
from typing import AsyncGenerator

import aiohttp
from bs4 import BeautifulSoup

from .constants import ARCH_NAMES, DISTRO_INFO, DISTRO_PACKAGE_SEARCH_URL


async def translate_sonames_to_deb_packages(
    distro_id: str, arch: str, sonames: tuple[str]
) -> set[str]:
    """Given a soname, lookup the deb package that provides it.

    Tools like 'apt-get -S' and 'apt-file' only work for the host's
    active distro and distro version. This code, however, should
    be able to run on any host even non-debian and non-ubuntu hosts.
    So, it uses an API call instead of local tooling.
    """
    distro = DISTRO_INFO.get(distro_id, {}).get("distro")
    search_url = DISTRO_PACKAGE_SEARCH_URL.get(distro)
    if not search_url:
        return set()

    # TODO: validate if always packagecloud_arch == debian_arch
    debian_arch = ARCH_NAMES.get(arch, {}).get("deb") or arch

    packages = set()
    async with aiohttp.ClientSession() as client:
        for soname in sonames:
            html_doc = await search_deb_packages(
                client, search_url, distro_id, debian_arch, soname
            )
            async for package, _ in deb_packages_from_html_response(html_doc):
                if package:
                    packages.add(package)

    return packages


async def search_deb_packages(
    client: aiohttp.ClientSession,
    search_url: str,
    distro_id: str,
    debian_arch: str,
    soname: str,
) -> str:
    """Use API to search for deb packages that contain soname.

    This HTTP+HTML package search API, sadly, does not support
    any format other than HTML (not JSON, YAML, etc).
    """
    # https://salsa.debian.org/webmaster-team/packages/-/blob/master/SEARCHES?ref_type=heads#L110-136
    query_params = {
        "format": "html",  # sadly, this API only supports format=html.
        "searchon": "contents",
        "mode": "exactfilename",  # soname should be exact filename.
        # mode=="" means find files where `filepath.endswith(keyword)`
        # mode=="filename" means find files where `keyword in filename`
        # mode=="exactfilename" means find files where `filename==keyword`
        "arch": debian_arch,
        "suite": distro_id,
        "keywords": soname,
    }

    # TODO: This needs to retry a few times as the API can be flaky
    async with client.get(search_url, params=query_params) as response:

        #response.status

        # sadly the "API" returns html and does not support other formats.
        html_doc = await response.text()

    return html_doc


async def deb_packages_from_html_response(html_doc: str) -> AsyncGenerator[tuple[str, tuple[str, ...]]]:
    """Extract deb packages from an HTML search response.

    This uses beautifulsoup to parse the search API's HTML responses with
    logic that is very similar to the MIT licensed apt-search CLI tool.
    This does not use apt-search directly because it is not meant to be
    a library, and it hardcodes the ubuntu package search URL.
    https://github.com/david-haerer/apt-search
    """

    # inspiration from (MIT licensed):
    # https://github.com/david-haerer/apt-search/blob/main/apt_search/main.py
    # (this script handles more API edge cases than apt-search and creates structured data)

    soup = BeautifulSoup(html_doc, "html.parser")

    # .table means 'search for a <table> tag'. The response should only have one.
    # In xmlpath, descending would look like one of these:
    #   /html/body/div[1]/div[3]/div[2]/table
    #   /html/body/div[@id="wrapper"]/div[@id="content"]/div[@id="pcontentsres"]/table
    results_table = soup.table

    if results_table is None:
        # No package(s) found
        return None

    # results_table is basically (nb: " [amd64] " is only present for arch=any and packages can be a list):
    #   <table>
    #     <tr><th>File</th><th>Packages</th></tr>
    #     <tr>
    #       <td class="file">/usr/lib/x86_64-linux-gnu/<span class="keyword">libldap-2.5.so.0</span></td>
    #       <td><a href="...">libldap-2.5.0</a> [amd64] </td>
    #     </tr>
    #     <tr>
    #       <td class="file">/usr/sbin/<span class="keyword">dnsmasq</span></td>
    #       <td><a href="...">dnsmasq-base</a>, <a href="...">dnsmasq-base-lua</a></td>
    #     </tr>
    #   </table>
    # But, html is semi-structured, so assume that it can be in a broken state.

    # files2packages: dict[str, list[str]] = {}
    packages2files: dict[str, list[str]] = defaultdict(list)
    for row in results_table.find_all("tr"):
        cells = tuple(row.find_all("td"))
        if len(cells) < 2:
            # ignore malformed rows with missing cell(s).
            continue
        file_cell, pkgs_cell = cells[:2]
        file_text = file_cell.get_text(strip=True)
        packages = list(
            pkg_a.get_text(strip=True) for pkg_a in pkgs_cell.find_all("a")
        )
        # files2packages[file_text] = packages
        for package in packages:
            packages2files[package].append(file_text)

    for package in sorted(packages2files):
        yield package, tuple(packages2files[package])
