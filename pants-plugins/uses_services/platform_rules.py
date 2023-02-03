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

from pants.backend.python.util_rules.pex import (
    PexRequest,
    PexRequirements,
    VenvPex,
    VenvPexProcess,
    rules as pex_rules,
)
from pants.engine.fs import CreateDigest, Digest, FileContent
from pants.engine.process import ProcessCacheScope, ProcessResult
from pants.engine.rules import collect_rules, Get, MultiGet, rule
from pants.util.logging import LogLevel

# noinspection PyProtectedMember
from uses_services.scripts.inspect_platform import (
    Platform,
    __file__ as inspect_platform_full_path,
)

__all__ = ["Platform", "get_platform", "rules"]


@rule(
    desc="Get details (os, distro, etc) about platform running tests.",
    level=LogLevel.DEBUG,
)
async def get_platform() -> Platform:
    script_path = "./inspect_platform.py"

    # pants is already watching this directory as it is under a source root.
    # So, we don't need to double watch with PathGlobs, just open it.
    with open(inspect_platform_full_path, "rb") as script_file:
        script_contents = script_file.read()

    script_digest, distro_pex = await MultiGet(
        Get(
            Digest,
            CreateDigest([FileContent(script_path, script_contents)]),
        ),
        Get(
            VenvPex,
            PexRequest(
                output_filename="distro.pex",
                internal_only=True,
                requirements=PexRequirements({"distro"}),
            ),
        ),
    )

    result = await Get(
        ProcessResult,
        VenvPexProcess(
            distro_pex,
            argv=(script_path,),
            input_digest=script_digest,
            description="Introspecting platform (arch, os, distro)",
            # this can change from run to run, so don't cache results.
            cache_scope=ProcessCacheScope.PER_RESTART_SUCCESSFUL,
            level=LogLevel.DEBUG,
        ),
    )
    platform = json.loads(result.stdout)
    return Platform(**platform)


def rules():
    return [
        *collect_rules(),
        *pex_rules(),
    ]
