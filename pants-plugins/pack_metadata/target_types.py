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
from typing import Sequence

from pants.engine.target import COMMON_TARGET_FIELDS, Dependencies
from pants.core.target_types import (
    ResourcesGeneratingSourcesField,
    ResourcesGeneratorTarget,
    GenericTarget,
)


class UnmatchedGlobsError(Exception):
    """Error thrown when a required set of globs didn't match."""


class PackMetadataSourcesField(ResourcesGeneratingSourcesField):
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


class PackMetadataInGitSubmoduleSources(PackMetadataSourcesField):
    required = True

    def validate_resolved_files(self, files: Sequence[str]) -> None:
        if not files:
            raise UnmatchedGlobsError(
                # see: st2tests.fixturesloader.GIT_SUBMODULES_NOT_CHECKED_OUT_ERROR
                "One or more git submodules is not checked out. Make sure to run "
                '"git submodule update --init --recursive"'
                "in the repository root directory to check out all the submodules."
            )
        super().validate_resolved_files(files)


class PackMetadata(ResourcesGeneratorTarget):
    alias = "pack_metadata"
    core_fields = (*COMMON_TARGET_FIELDS, Dependencies, PackMetadataSourcesField)
    help = (
        "Loose pack metadata files.\n\n"
        "Pack metadata includes top-level files (pack.yaml, <pack>.yaml.example, "
        "config.schema.yaml, and icon.png) and metadata for actions, "
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


class PacksGlobDependencies(Dependencies):
    pass


class PacksGlob(GenericTarget):
    alias = "packs_glob"
    core_fields = (*COMMON_TARGET_FIELDS, PacksGlobDependencies)
    help = (
        "Packs glob.\n\n"
        "Avoid using this target. It gets automatic dependencies on all "
        "subdirectories (packs) except those listed with ! in dependencies. "
        "This is unfortunately needed by tests that use a glob to load pack fixtures."
    )
