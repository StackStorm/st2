import dataclasses

from typing import Sequence

from pants.engine.addresses import Address, Addresses
from pants.engine.fs import (
    GlobMatchErrorBehavior,
    PathGlobs,
    Paths,
)
from pants.engine.rules import Get, MultiGet
from pants.engine.target import (
    COMMON_TARGET_FIELDS,
    Dependencies,
    DependenciesRequest,
    Sources,
    StringField,
    Target,
    WrappedTarget,
)


class MessageOnErrorField(StringField):
    alias = "message_on_error"
    required = True
    help = "The message to warn with when the dependency globs do not match."


# See `target_types_rules.py` for a dependency injection rule.
class UnmatchedGlobsDependencies(Dependencies):
    required = True


class UnmatchedGlobsSources(Sources):
    def validate_resolved_files(self, files: Sequence[str]) -> None:
        original_tgt: WrappedTarget = await Get(
            WrappedTarget, Address, self.address
        )

        error_message = original_tgt.target[MessageOnErrorField]

        dependencies = await Get(
            Addresses,
            DependenciesRequest(original_tgt.target[UnmatchedGlobsDependencies])
        )
        dependency_targets = await MultiGet(
            Get(WrappedTarget, Address, address)
            for address in dependencies
        )

        sources_fields = [
            wrapped_tgt.target.get(field)
            for wrapped_tgt in dependency_targets
            for field in wrapped_tgt.target
            if (isinstance(field, Sources) and wrapped_tgt.target.get(field))
        ]

        path_globs = [
            dataclasses.replace(
                source_field.path_globs(),
                glob_match_error_behavior=GlobMatchErrorBehavior.error,
                description_of_origin=error_message,
            )
            for source_field in sources_fields
        ]

        # Use the engine to error when the globs do not match
        await MultiGet(
            Get(
                Paths,
                PathGlobs,
                path_glob
            ) for path_glob in path_globs
        )


class UnmatchedGlobsTarget(Target):
    alias = "unmatched_globs"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        UnmatchedGlobsSources,
        UnmatchedGlobsDependencies,
        MessageOnErrorField,
    )
    help = "Declare an error message to show when dependency globs do not match."
