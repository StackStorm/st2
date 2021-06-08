import dataclasses

from typing import Any, Dict, Optional, Sequence
from typing_extensions import final

from pants.backend.python.target_types import (
    InterpreterConstraintsField,
    PythonLibrary,
    PythonLibrarySources,
)
from pants.engine.addresses import Address
from pants.engine.target import (
    AsyncFieldMixin,
    COMMON_TARGET_FIELDS,
    Dependencies,
    StringField,
    Target,
)
from pants.engine.unions import UnionMembership

from pack_metadata.target_types import PackMetadata, PackMetadataSources


class UnmatchedGlobsError(Exception):
    """Error thrown when a required set of globs didn't match."""


class MessageOnUnmatchedGlobsField(StringField):
    alias = "message_on_unmatched_globs"
    required = True
    help = "The message to warn with when the sources field has unmatched globs."


class NoUnmatchedGlobsSourcesMixin(AsyncFieldMixin):
    def validate_resolved_files(self, files: Sequence[str]) -> None:
        if not files:
            raise UnmatchedGlobsError("inner unmatched globs error")


class PythonLibrarySourcesNoUnmatchedGlobs(
    NoUnmatchedGlobsSourcesMixin, PythonLibrarySources
):
    required = True


class PackMetadataSourcesNoUnmatchedGlobs(
    NoUnmatchedGlobsSourcesMixin, PackMetadataSources
):
    required = True


class UnmatchedGlobsTargetMixin(Target):
    @final
    def __init__(
        self,
        unhydrated_values: Dict[str, Any],
        address: Address,
        *,
        union_membership: Optional[UnionMembership] = None,
    ) -> None:
        unmatched_globs_error_msg = unhydrated_values.get(
            MessageOnUnmatchedGlobsField.alias, "There were unmatched_globs!"
        )
        try:
            super(UnmatchedGlobsTargetMixin, self).__init__(
                unhydrated_values, address, union_membership=union_membership
            )
        except UnmatchedGlobsError:
            raise UnmatchedGlobsError(unmatched_globs_error_msg)


_unmatched_globs_help = """
The *_no_unmatched_globs variant errors if the sources field has unmatched globs.
When it errors, it prints the message from the `message_on_unmatched_globs` field.
"""


class PythonLibraryNoUnmatchedGlobs(UnmatchedGlobsTargetMixin, PythonLibrary):
    alias = "python_library_no_unmatched_globs"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        InterpreterConstraintsField,
        Dependencies,
        PythonLibrarySourcesNoUnmatchedGlobs,
        MessageOnUnmatchedGlobsField,
    )
    help = PythonLibrary.help + _unmatched_globs_help


class PackMetadataNoUnmatchedGlobs(UnmatchedGlobsTargetMixin, PackMetadata):
    alias = "pack_metadata_no_unmatched_globs"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        Dependencies,
        PackMetadataSourcesNoUnmatchedGlobs,
        MessageOnUnmatchedGlobsField,
    )
    help = PackMetadata.help + _unmatched_globs_help
