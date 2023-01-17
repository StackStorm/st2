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
import os
from dataclasses import dataclass

from pants.core.goals.tailor import (
    AllOwnedSources,
    PutativeTarget,
    PutativeTargets,
    PutativeTargetsRequest,
)
from pants.engine.fs import PathGlobs, Paths
from pants.engine.rules import collect_rules, Get, rule, UnionRule
from pants.util.logging import LogLevel

from pack_metadata.target_types import PackMetadata


@dataclass(frozen=True)
class PutativePackMetadataTargetsRequest(PutativeTargetsRequest):
    pass


@rule(
    desc="Find pack (config, action, alias, sensor, icon, etc) metadata files.",
    level=LogLevel.DEBUG,
)
async def find_putative_targets(
    _: PutativePackMetadataTargetsRequest, all_owned_sources: AllOwnedSources
) -> PutativeTargets:
    all_pack_yaml_files = await Get(Paths, PathGlobs(["**/pack.yaml"]))

    unowned_pack_yaml_files = set(all_pack_yaml_files.files) - set(all_owned_sources)
    unowned_pack_dirs = [os.path.dirname(p) for p in unowned_pack_yaml_files]

    name = "metadata"
    return PutativeTargets(
        [
            PutativeTarget.for_target_type(
                PackMetadata, dirname, name, ("pack.yaml",), kwargs={"name": name}
            )
            for dirname in unowned_pack_dirs
        ]
    )


def rules():
    return [
        *collect_rules(),
        UnionRule(PutativeTargetsRequest, PutativePackMetadataTargetsRequest),
    ]
