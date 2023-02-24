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
from __future__ import annotations

from .platform_rules import Platform


def platform(
    arch="",
    os="",
    distro="",
    distro_name="",
    distro_codename="",
    distro_like="",
    distro_major_version="",
    distro_version="",
    mac_release="",
    win_release="",
) -> Platform:
    """Create a Platform with all values defaulted to the empty string."""
    return Platform(
        arch=arch,
        os=os,
        distro=distro,
        distro_name=distro_name,
        distro_codename=distro_codename,
        distro_like=distro_like,
        distro_major_version=distro_major_version,
        distro_version=distro_version,
        mac_release=mac_release,
        win_release=win_release,
    )


platform_samples = (
    platform(),  # empty
    # EL distros ##################
    platform(
        arch="x86_64",
        os="Linux",
        distro="centos",
        distro_name="Centos Linux",
        distro_codename="Core",
        distro_like="rhel fedora",
        distro_major_version="7",
        distro_version="7",
    ),
    platform(
        arch="x86_64",
        os="Linux",
        distro="rocky",
        distro_name="Rocky Linux",
        distro_codename="Green Obsidian",
        distro_like="rhel centos fedora",
        distro_major_version="8",
        distro_version="8.7",
    ),
    # debian distros ##############
    platform(
        arch="x86_64",
        os="Linux",
        distro="ubuntu",
        distro_name="Ubuntu",
        distro_codename="xenial",
        distro_like="debian",
        distro_major_version="16",
        distro_version="16.04",
    ),
    platform(
        arch="x86_64",
        os="Linux",
        distro="ubuntu",
        distro_name="Ubuntu",
        distro_codename="bionic",
        distro_like="debian",
        distro_major_version="18",
        distro_version="18.04",
    ),
    platform(
        arch="x86_64",
        os="Linux",
        distro="ubuntu",
        distro_name="Ubuntu",
        distro_codename="focal",
        distro_like="debian",
        distro_major_version="20",
        distro_version="20.04",
    ),
    # other Linux distros #########
    platform(
        arch="x86_64",
        os="Linux",
        distro="gentoo",
        distro_name="Gentoo",
        distro_codename="n/a",
        distro_major_version="2",
        distro_version="2.7",
    ),
    platform(
        arch="aarch64",
        os="Linux",
        # no distro in termux on android
    ),
    # platform(
    #    arch="x86_64",
    #    os="Linux",
    #    distro="",
    #    distro_name="",
    #    distro_codename="",
    #    distro_like="",
    #    distro_major_version="",
    #    distro_version="",
    # ),
    # Mac OS X ####################
    platform(
        arch="x86_64",
        os="Darwin",
        distro="darwin",
        distro_name="Darwin",
        distro_major_version="19",
        distro_version="19.6.0",
        mac_release="10.15.7",
    ),
    platform(
        arch="x86_64",
        os="Darwin",
        distro="darwin",
        distro_name="Darwin",
        distro_major_version="21",
        distro_version="21.6.0",
        mac_release="12.6.2",
    ),
)
