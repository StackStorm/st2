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
from enum import Enum
from pathlib import PurePath
from typing import Optional, Sequence, Tuple

from pants.engine.internals.native_engine import Address
from pants.engine.target import (
    BoolField,
    COMMON_TARGET_FIELDS,
    Dependencies,
    StringField,
)
from pants.core.target_types import (
    ResourceDependenciesField,
    ResourcesGeneratingSourcesField,
    ResourcesGeneratorTarget,
    ResourcesOverridesField,
    ResourceSourceField,
    ResourceTarget,
    GenericTarget,
)


class UnmatchedGlobsError(Exception):
    """Error thrown when a required set of globs didn't match."""


class PackContentResourceTypes(Enum):
    # in root of pack
    pack_metadata = "pack_metadata"
    pack_config_schema = "pack_config_schema"
    pack_config_example = "pack_config_example"
    pack_icon = "pack_icon"
    # in subdirectory (see _content_type_by_path_parts below
    action_metadata = "action_metadata"
    action_chain_workflow = "action_chain_workflow"
    orquesta_workflow = "orquesta_workflow"
    alias_metadata = "alias_metadata"
    policy_metadata = "policy_metadata"
    rule_metadata = "rule_metadata"
    sensor_metadata = "sensor_metadata"
    trigger_metadata = "trigger_metadata"
    # other
    unknown = "unknown"


_content_type_by_path_parts: dict[Tuple[str, ...], PackContentResourceTypes] = {
    ("actions",): PackContentResourceTypes.action_metadata,
    ("actions", "chains"): PackContentResourceTypes.action_chain_workflow,
    ("actions", "workflows"): PackContentResourceTypes.orquesta_workflow,
    ("aliases",): PackContentResourceTypes.alias_metadata,
    ("policies",): PackContentResourceTypes.policy_metadata,
    ("rules",): PackContentResourceTypes.rule_metadata,
    ("sensors",): PackContentResourceTypes.sensor_metadata,
    ("triggers",): PackContentResourceTypes.trigger_metadata,
}


class PackContentResourceTypeField(StringField):
    alias = "type"
    help = (
        "The content type of the resource."
        "\nDo not use this field in BUILD files. It is calculated automatically"
        "based on the conventional location of files in the st2 pack."
    )
    valid_choices = PackContentResourceTypes
    value: PackContentResourceTypes

    @classmethod
    def compute_value(
        cls, raw_value: Optional[str], address: Address
    ) -> PackContentResourceTypes:
        value = super().compute_value(raw_value, address)
        if value is not None:
            return PackContentResourceTypes(value)
        path = PurePath(address.relative_file_path)
        _yaml_suffixes = (".yaml", ".yml")
        if len(path.parent.parts) == 0:
            # in the pack root
            if path.stem == "pack" and path.suffix in _yaml_suffixes:
                return PackContentResourceTypes.pack_metadata
            if path.stem == "config.schema" and path.suffix in _yaml_suffixes:
                return PackContentResourceTypes.pack_config_schema
            if (
                path.stem.startswith("config.")
                and path.suffixes[0] in _yaml_suffixes
                and path.suffix == ".example"
            ):
                return PackContentResourceTypes.pack_config_example
            if path.name == "icon.png":
                return PackContentResourceTypes.pack_icon
            return PackContentResourceTypes.unknown
        resource_type = _content_type_by_path_parts.get(path.parent.parts, None)
        if resource_type is not None:
            return resource_type
        return PackContentResourceTypes.unknown


class PackContentResourceSourceField(ResourceSourceField):
    pass


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
        # exclude yaml files under tests
        "!tests/**/*.yml",
        "!tests/**/*.yaml",
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


class PackContentResourceTarget(ResourceTarget):
    alias = "pack_content_resource"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        ResourceDependenciesField,
        PackContentResourceSourceField,
        PackContentResourceTypeField,
    )
    help = "A single pack content resource file (mostly for metadata files)."


class PackMetadata(ResourcesGeneratorTarget):
    alias = "pack_metadata"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        PackMetadataSourcesField,
        ResourcesOverridesField,
    )
    moved_fields = (ResourceDependenciesField,)
    generated_target_cls = PackContentResourceTarget
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
        PackMetadataInGitSubmoduleSources,
        ResourcesOverridesField,
    )
    moved_fields = (ResourceDependenciesField,)
    generated_target_cls = PackContentResourceTarget
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


class InjectPackPythonPathField(BoolField):
    alias = "inject_pack_python_path"
    help = (
        "For pack tests, set this to true to make sure <pack>/lib or actions/ dirs get "
        "added to PYTHONPATH (actually PEX_EXTRA_SYS_PATH). Use `__defaults__` to enable "
        "this in the BUILD file where you define pack_metadata, like this: "
        "`__defaults__(all=dict(inject_pack_python_path=True))`"
    )
    default = False
