# coding: utf-8
# repurposed from pants.backend.python.target_types_rules
import dataclasses
import os

from pants.backend.python.dependency_inference.module_mapper import PythonModule, PythonModuleOwners
from pants.backend.python.dependency_inference.rules import PythonInferSubsystem, import_rules
from pants.engine.addresses import Address
from pants.engine.fs import GlobMatchErrorBehavior, PathGlobs, Paths
from pants.engine.rules import Get, collect_rules, MultiGet, rule, UnionRule
from pants.engine.target import (
    Dependencies,
    DependenciesRequest,
    ExplicitlyProvidedDependencies,
    InjectDependenciesRequest,
    InjectedDependencies,
    InvalidFieldException,
    WrappedTarget,
)
from pants.source.source_root import SourceRoot, SourceRootRequest

from stevedore_extensions.target_types import (
    ResolvedStevedoreEntryPoints,
    ResolveStevedoreEntryPointsRequest,
    StevedoreDependencies,
    StevedoreEntryPoints,
    StevedoreEntryPointsField,
)


@rule(desc="Determining the entry points for a `stevedore_extension` target")
async def resolve_stevedore_entry_points(request: ResolveStevedoreEntryPointsRequest) -> ResolvedStevedoreEntryPoints:
    address = request.entry_points_field.address
    resolved = []
    for entry_point in request.entry_points_field.value:
        ep_val = entry_point.value

        # supported schemes mirror those in resolve_pex_entry_point:
        #  1) this does not support None, unlike pex_entry_point.
        #  2) `path.to.module` => preserve exactly.
        #  3) `path.to.module:func` => preserve exactly.
        #  4) `app.py` => convert into `path.to.app`.
        #  5) `app.py:func` => convert into `path.to.app:func`.

        # If it's already a module (cases #2 and #3), simply use that. Otherwise, convert the file name
        # into a module path (cases #4 and #5).
        if not ep_val.module.endswith(".py"):
            resolved.append(entry_point)
            continue

        # Use the engine to validate that the file exists and that it resolves to only one file.
        full_glob = os.path.join(address.spec_path, ep_val.module)
        entry_point_paths = await Get(
            Paths,
            PathGlobs(
                [full_glob],
                glob_match_error_behavior=GlobMatchErrorBehavior.error,
                description_of_origin=f"{address}'s `{request.entry_points_field.alias}` field",
            )
        )
        # We will have already raised if the glob did not match, i.e. if there were no files. But
        # we need to check if they used a file glob (`*` or `**`) that resolved to >1 file.
        if len(entry_point_paths.files) != 1:
            raise InvalidFieldException(
                f"Multiple files matched for the `{request.entry_points_field.alias}` "
                f"{ep_val.spec!r} for the target {address}, but only one file expected. Are you using "
                f"a glob, rather than a file name?\n\n"
                f"All matching files: {list(entry_point_paths.files)}."
            )
        entry_point_path = entry_point_paths.files[0]
        source_root = await Get(
            SourceRoot,
            SourceRootRequest,
            SourceRootRequest.for_file(entry_point_path),
        )
        stripped_source_path = os.path.relpath(entry_point_path, source_root.path)
        module_base, _ = os.path.splitext(stripped_source_path)
        normalized_path = module_base.replace(os.path.sep, ".")
        resolved_ep_val = dataclasses.replace(ep_val, module=normalized_path)
        resolved.append(dataclasses.replace(entry_point, value=resolved_ep_val))
    return ResolvedStevedoreEntryPoints(StevedoreEntryPoints(resolved))


class InjectStevedoreExtensionDependencies(InjectDependenciesRequest):
    inject_for = StevedoreDependencies


@rule(desc="Inferring dependency from the stevedore_extension `entry_points` field")
async def inject_stevedore_entry_points_dependencies(
    request: InjectStevedoreExtensionDependencies, python_infer_subsystem: PythonInferSubsystem
) -> InjectedDependencies:
    # TODO: this might not be the best option to use as it is for "binary targets"
    # if not python_infer_subsystem.entry_points:
    #     return InjectedDependencies()
    original_tgt: WrappedTarget
    original_tgt = await Get(WrappedTarget, Address, request.dependencies_field.address)
    entry_points: ResolvedStevedoreEntryPoints
    explicitly_provided_deps, entry_points = await MultiGet(
        Get(ExplicitlyProvidedDependencies, DependenciesRequest(original_tgt.target[Dependencies])),
        Get(
            ResolvedStevedoreEntryPoints,
            ResolveStevedoreEntryPointsRequest(original_tgt.target[StevedoreEntryPointsField])
        ),
    )
    if entry_points.val is None:
        return InjectedDependencies()
    address = original_tgt.target.address
    owners_per_entry_point = await MultiGet(
        Get(PythonModuleOwners, PythonModule(entry_point.value.module))
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
                f"`\"{entry_point.name}\": \"{repr(original_ep.value.spec)}\"`,"
                f"which maps to the Python module `{entry_point.value.module}`"
            ),
        )
        maybe_disambiguated = explicitly_provided_deps.disambiguated_via_ignores(owners.ambiguous)
        unambiguous_owners = owners.unambiguous or (
            (maybe_disambiguated,) if maybe_disambiguated else ()
        )
        resolved_owners.extend(unambiguous_owners)
    return InjectedDependencies(resolved_owners)


def rules():
    return [
        *collect_rules(),
        *import_rules(),
        UnionRule(InjectDependenciesRequest, InjectStevedoreExtensionDependencies),
    ]
