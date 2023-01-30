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

from pants.engine.addresses import Address
from pants.engine.fs import GlobMatchErrorBehavior, PathGlobs, Paths
from pants.engine.rules import Get, collect_rules, MultiGet, rule, UnionRule
from pants.engine.target import (
    DependenciesRequest,
    ExplicitlyProvidedDependencies,
    FieldSet,
    InferDependenciesRequest,
    InferredDependencies,
)
from pants.util.logging import LogLevel

from pack_metadata.target_types import PacksGlobDependencies


@dataclass(frozen=True)
class PacksGlobInferenceFieldSet(FieldSet):
    required_fields = (PacksGlobDependencies,)

    dependencies: PacksGlobDependencies


class InferPacksGlobDependencies(InferDependenciesRequest):
    infer_from = PacksGlobInferenceFieldSet


@rule(
    desc="Inferring packs glob dependencies",
    level=LogLevel.DEBUG,
)
async def infer_packs_globs_dependencies(
    request: InferPacksGlobDependencies,
) -> InferredDependencies:
    address = request.field_set.address

    pack_build_paths, explicitly_provided_deps = await MultiGet(
        Get(
            Paths,
            PathGlobs(
                [os.path.join(address.spec_path, "*", "BUILD")],
                glob_match_error_behavior=GlobMatchErrorBehavior.error,
                description_of_origin=f"{address}'s packs glob",
            ),
        ),
        Get(
            ExplicitlyProvidedDependencies,
            DependenciesRequest(request.field_set.dependencies),
        ),
    )

    implicit_packs_deps = {
        Address(os.path.dirname(path)) for path in pack_build_paths.files
    }

    inferred_packs_deps = (
        implicit_packs_deps
        - explicitly_provided_deps.ignores  # FrozenOrderedSet[Address]
        - explicitly_provided_deps.includes  # FrozenOrderedSet[Address]
    )
    return InferredDependencies(inferred_packs_deps)


def rules():
    return [
        *collect_rules(),
        UnionRule(InferDependenciesRequest, InferPacksGlobDependencies),
    ]
