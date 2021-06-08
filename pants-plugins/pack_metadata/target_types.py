from typing import Sequence

from pants.engine.target import COMMON_TARGET_FIELDS, Dependencies, Target
from pants.core.target_types import FilesSources


class UnmatchedGlobsError(Exception):
    """Error thrown when a required set of globs didn't match."""


class PackMetadataSources(FilesSources):
    required = False
    default = (
        # metadata does not include any python, shell, or other sources.
        "pack.yaml",
        "config.schema.yaml",
        "*.yaml.example",
        "**/*.yaml",
        "**/*.yml",
        "icon.png",  # used in st2web ui
        # "requirements*.txt",  # including this causes target conflicts
        # "README.md",
        # "HISTORY.md",
    )


class PackMetadataInGitSubmoduleSources(PackMetadataSources):
    required = True

    def validate_resolved_files(self, files: Sequence[str]) -> None:
        if not files:
            raise UnmatchedGlobsError("Instructions go here")
        super().validate_resolved_files(files)


class PackMetadata(Target):
    alias = "pack_metadata"
    core_fields = (*COMMON_TARGET_FIELDS, Dependencies, PackMetadataSources)
    help = (
        "Loose pack metadata files.\n\n"
        "Pack metadata includes top-level files (pack.yaml, <pack>.yaml.examle, "
        "config.schema.yaml, icon.png, and requirements.txt) and metadata for actions, "
        "action-aliases, policies, rules, and sensors."
    )


class PackMetadataInGitSubmodule(PackMetadata):
    alias = "pack_metadata_in_git_submodule"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        Dependencies,
        PackMetadataInGitSubmoduleSources,
    )
    help = PackMetadata.help + (
        "\npack_metadata_in_git_submodule variant errors if the sources field "
        "has unmatched globs. It prints instructions on how to checkout git "
        "submodules."
    )
