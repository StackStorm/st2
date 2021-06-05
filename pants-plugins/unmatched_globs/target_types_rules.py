from pants.backend.python.dependency_inference.rules import import_rules
from pants.engine.addresses import Address, Addresses
from pants.engine.fs import (
    GlobExpansionConjunction,
    GlobMatchErrorBehavior,
    PathGlobs,
    Paths,
)
from pants.engine.rules import Get, collect_rules, MultiGet, rule, UnionRule
from pants.engine.target import (
    DependenciesRequest,
    InjectDependenciesRequest,
    InjectedDependencies,
    Sources,
    WrappedTarget,
)

from unmatched_globs.target_types import UnmatchedGlobsDependencies, MessageOnErrorField


class InjectUnmatchedGlobsDependenciesRequest(InjectDependenciesRequest):
    inject_for = UnmatchedGlobsDependencies


# rule will not be visible in list of running rules
@rule(desc="Check for dependencies' unmatched globs to provide helpful error message.")
async def helpful_message_for_git_submodule(
    request: InjectUnmatchedGlobsDependenciesRequest,
) -> InjectedDependencies:
    original_tgt: WrappedTarget = await Get(
        WrappedTarget, Address, request.dependencies_field.address
    )

    dependencies = await Get(
        Addresses,
        DependenciesRequest(original_tgt.target[UnmatchedGlobsDependencies])
    )
    dependency_targets = await MultiGet(
        Get(WrappedTarget, Address, address)
        for address in dependencies
    )

    # the following is roughly based on Sources.path_globs

    sources_fields = [
        wrapped_tgt.target.get(field)
        for wrapped_tgt in dependency_targets
        for field in wrapped_tgt.target if (isinstance(field, Sources) and target.get(field))
    ]
    # noinspection PyProtectedMember
    source_globs = [
        source_field._prefix_glob_with_address(source_glob)
        for source_field in sources_fields
        if not source_field.default or set(source_field.value or ()) != set(source_field.default)
        for source_glob in source_field.value or ()
    ]

    error_message = original_tgt.target[MessageOnErrorField]

    # Use the engine to warn when the globs do not match
    await Get(
        Paths,
        PathGlobs(
            source_globs,
            conjunction=GlobExpansionConjunction.all_match,
            glob_match_error_behavior=GlobMatchErrorBehavior.warn,
            description_of_origin=error_message,
        )
    )

    return InjectedDependencies()


def rules():
    return [
        *collect_rules(),
        *import_rules(),
        UnionRule(InjectDependenciesRequest, InjectUnmatchedGlobsDependenciesRequest),
    ]
