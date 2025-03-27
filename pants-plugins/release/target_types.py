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

from pants.backend.nfpm.target_types import NfpmDebPackage, NfpmRpmPackage
from pants.engine.target import StringField
from pants.util.strutil import help_text


class DistroIDField(StringField):
    nfpm_alias = ""  # Not an nFPM field
    alias = "distro_id"
    valid_choices = (  # officially supported (or planned future support)
        # ubuntu
        "focal",
        "jammy",
        "noble",
        # el
        "el8",
        "el9",
    )
    required = True
    help = help_text(
        """
        The package distribution and version.

        This is an internal StackStorm field used by pants-plugins/release.
        The IDs are StackStorm-specific IDs that get translated into distribution + version.
        These examples show how the distro_id gets translated into packagecloud values:
          - distro_id "el8" is distro "el" with version "8";
          - distro_id "focal" is distro "ubuntu" with version "focal".
        """
    )


def rules():
    return [
        NfpmDebPackage.register_plugin_field(DistroIDField),
        NfpmRpmPackage.register_plugin_field(DistroIDField),
    ]
