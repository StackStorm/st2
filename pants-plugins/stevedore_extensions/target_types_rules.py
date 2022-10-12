# Copyright 2021 The StackStorm Authors.
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
# repurposed from pants.backend.python.target_types_rules
import dataclasses
import os

from pants.backend.python.dependency_inference.module_mapper import (
    PythonModuleOwners,
    PythonModuleOwnersRequest,
)
from pants.backend.python.dependency_inference.rules import import_rules
from pants.backend.python.subsystems.setup import PythonSetup
from pants.backend.python.target_types import PythonResolveField
from pants.engine.fs import GlobMatchErrorBehavior, PathGlobs, Paths
from pants.engine.rules import Get, collect_rules, MultiGet, rule, UnionRule
from pants.engine.target import (
    AllTargets,
    Dependencies,
    DependenciesRequest,
    ExplicitlyProvidedDependencies,
    InferDependenciesRequest,
    InferredDependencies,
    InvalidFieldException,
    WrappedTarget,
    WrappedTargetRequest,
)
from pants.source.source_root import SourceRoot, SourceRootRequest
from pants.util.logging import LogLevel

from stevedore_extensions.target_types import (
    AllStevedoreExtensionTargets,
    ResolvedStevedoreEntryPoints,
    ResolveStevedoreEntryPointsRequest,
    StevedoreDependenciesField,
    StevedoreEntryPoints,
    StevedoreEntryPointsField,
)


@rule(desc="Find all StevedoreExtension targets in project", level=LogLevel.DEBUG)
def find_all_stevedore_extension_targets(
    targets: AllTargets,
) -> AllStevedoreExtensionTargets:
    return AllStevedoreExtensionTargets(
        tgt for tgt in targets if tgt.has_field(StevedoreDependenciesField)
    )


@rule(
    desc="Determining the entry points for a `stevedore_extension` target",
    level=LogLevel.DEBUG,
)
async def resolve_stevedore_entry_points(
    request: ResolveStevedoreEntryPointsRequest,
) -> ResolvedStevedoreEntryPoints:

    # supported schemes mirror those in resolve_pex_entry_point:
    #  1) this does not support None, unlike pex_entry_point.
    #  2) `path.to.module` => preserve exactly.
    #  3) `path.to.module:func` => preserve exactly.
    #  4) `app.py` => convert into `path.to.app`.
    #  5) `app.py:func` => convert into `path.to.app:func`.

    address = request.entry_points_field.address

    # Use the engine to validate that any file exists
    entry_point_paths_results = await MultiGet(
        Get(
            Paths,
            PathGlobs(
                [os.path.join(address.spec_path, entry_point.value.module)],
                glob_match_error_behavior=GlobMatchErrorBehavior.error,
                description_of_origin=f"{address}'s `{request.entry_points_field.alias}` field",
            ),
        )
        for entry_point in request.entry_points_field.value
        if entry_point.value.module.endswith(".py")
    )

    # use iter so we can use next() below
    iter_entry_point_paths_results = iter(entry_point_paths_results)

    # We will have already raised if the glob did not match, i.e. if there were no files. But
    # we need to check if they used a file glob (`*` or `**`) that resolved to >1 file.
    for entry_point in request.entry_points_field.value:
        # We just need paths here. If it's already a path, skip it until the next loop.
        if not entry_point.value.module.endswith(".py"):
            continue

        entry_point_paths = next(iter_entry_point_paths_results)
        if len(entry_point_paths.files) != 1:
            raise InvalidFieldException(
                f"Multiple files matched for the `{request.entry_points_field.alias}` "
                f"{entry_point.value.spec!r} for the target {address}, but only one file expected. Are you using "
                f"a glob, rather than a file name?\n\n"
                f"All matching files: {list(entry_point_paths.files)}."
            )

    # restart the iterator
    iter_entry_point_paths_results = iter(entry_point_paths_results)

    source_root_results = await MultiGet(
        Get(
            SourceRoot,
            SourceRootRequest,
            SourceRootRequest.for_file(next(iter_entry_point_paths_results).files[0]),
        )
        for entry_point in request.entry_points_field.value
        if entry_point.value.module.endswith(".py")
    )

    # restart the iterator
    iter_entry_point_paths_results = iter(entry_point_paths_results)
    iter_source_root_results = iter(source_root_results)

    resolved = []
    for entry_point in request.entry_points_field.value:
        # If it's already a module (cases #2 and #3), we'll just use that.
        # Otherwise, convert the file name into a module path (cases #4 and #5).
        if not entry_point.value.module.endswith(".py"):
            resolved.append(entry_point)
            continue

        entry_point_path = next(iter_entry_point_paths_results).files[0]
        source_root = next(iter_source_root_results)

        stripped_source_path = os.path.relpath(entry_point_path, source_root.path)
        module_base, _ = os.path.splitext(stripped_source_path)
        normalized_path = module_base.replace(os.path.sep, ".")
        resolved_ep_val = dataclasses.replace(entry_point.value, module=normalized_path)
        resolved.append(dataclasses.replace(entry_point, value=resolved_ep_val))
    return ResolvedStevedoreEntryPoints(StevedoreEntryPoints(resolved))


class InferStevedoreExtensionDependencies(InferDependenciesRequest):
    inject_for = StevedoreDependenciesField


@rule(
    desc="Inferring dependency from the stevedore_extension `entry_points` field",
    level=LogLevel.DEBUG,
)
async def inject_stevedore_entry_points_dependencies(
    request: InferStevedoreExtensionDependencies,
    python_setup: PythonSetup,
) -> InferredDependencies:
    original_tgt: WrappedTarget = await Get(
        WrappedTarget,
        WrappedTargetRequest(
            request.dependencies_field.address,
            description_of_origin="inject_stevedore_entry_points_dependencies",
        ),
    )
    entry_points: ResolvedStevedoreEntryPoints
    explicitly_provided_deps, entry_points = await MultiGet(
        Get(
            ExplicitlyProvidedDependencies,
            DependenciesRequest(original_tgt.target[Dependencies]),
        ),
        Get(
            ResolvedStevedoreEntryPoints,
            ResolveStevedoreEntryPointsRequest(
                original_tgt.target[StevedoreEntryPointsField]
            ),
        ),
    )
    if entry_points.val is None:
        return InferredDependencies()
    address = original_tgt.target.address
    owners_per_entry_point = await MultiGet(
        Get(
            PythonModuleOwners,
            PythonModuleOwnersRequest(
                entry_point.value.module,
                resolve=original_tgt.target[PythonResolveField].normalized_value(
                    python_setup
                ),
            ),
        )
        for entry_point in entry_points.val
    )
    original_entry_points = original_tgt.target[StevedoreEntryPointsField].value
    resolved_owners = []
    for entry_point, owners, original_ep in zip(
        entry_points.val, owners_per_entry_point, original_entry_points
    ):
        explicitly_provided_deps.maybe_warn_of_ambiguous_dependency_inference(
            owners.ambiguous,
            address,
            import_reference="module",
            context=(
                f"The stevedore_extension target {address} has in its entry_points field "
                f'`"{entry_point.name}": "{repr(original_ep.value.spec)}"`,'
                f"which maps to the Python module `{entry_point.value.module}`"
            ),
        )
        maybe_disambiguated = explicitly_provided_deps.disambiguated(owners.ambiguous)
        unambiguous_owners = owners.unambiguous or (
            (maybe_disambiguated,) if maybe_disambiguated else ()
        )
        resolved_owners.extend(unambiguous_owners)
    return InferredDependencies(resolved_owners)


def rules():
    return [
        *collect_rules(),
        *import_rules(),
        UnionRule(InferDependenciesRequest, InferStevedoreExtensionDependencies),
    ]
