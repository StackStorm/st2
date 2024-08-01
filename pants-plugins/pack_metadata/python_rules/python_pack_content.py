# Copyright 2024 The StackStorm Authors.
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
from dataclasses import dataclass

from pants.engine.rules import collect_rules, rule
from pants.engine.target import (
    AllTargets,
    Targets,
)
from pants.util.logging import LogLevel

from pack_metadata.target_types import (
    PackContentResourceSourceField,
    PackContentResourceTypeField,
    PackContentResourceTypes,
    PackMetadata,
)


@dataclass(frozen=True)
class PackContentResourceTargetsOfTypeRequest:
    types: tuple[PackContentResourceTypes, ...]


class PackContentResourceTargetsOfType(Targets):
    pass


@rule(
    desc=f"Find all `{PackMetadata.alias}` targets in project filtered by content type",
    level=LogLevel.DEBUG,
)
async def find_pack_metadata_targets_of_types(
    request: PackContentResourceTargetsOfTypeRequest, targets: AllTargets
) -> PackContentResourceTargetsOfType:
    return PackContentResourceTargetsOfType(
        tgt
        for tgt in targets
        if tgt.has_field(PackContentResourceSourceField)
        and (
            not request.types
            or tgt[PackContentResourceTypeField].value in request.types
        )
    )


def rules():
    return (*collect_rules(),)
