from typing import Sequence
from pants.engine.target import COMMON_TARGET_FIELDS, Dependencies

from pack_metadata.target_types import PackMetadata, PackMetadataSources


class UnmatchedGlobsError(Exception):
    """Error thrown when a required set of globs didn't match."""


class PackMetadataInGitSubmoduleSources(PackMetadataSources):
    required = True

    def validate_resolved_files(self, files: Sequence[str]) -> None:
        if not files:
            raise UnmatchedGlobsError("Instructions go here")
        super().validate_resolved_files(files)


class PackMetadataInGitSubmodule(PackMetadata):
    alias = "pack_metadata_in_git_submodule"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        Dependencies,
        PackMetadataInGitSubmoduleSources,
    )
    help = PackMetadata.help + """
The *_in_git_submodule variant errors if the sources field has unmatched globs.
It prints instructions on how to checkout the git submodules.
"""
