# Copyright 2024 The StackStorm Authors.
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
import yaml
from collections import defaultdict
from dataclasses import dataclass
from pathlib import PurePath
from typing import DefaultDict

from pants.backend.python.subsystems.setup import PythonSetup
from pants.backend.python.target_types import PythonResolveField
from pants.base.glob_match_error_behavior import GlobMatchErrorBehavior
from pants.base.specs import FileLiteralSpec, RawSpecs
from pants.engine.collection import Collection
from pants.engine.fs import DigestContents
from pants.engine.internals.native_engine import Address, Digest
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import (
    AllTargets,
    HydrateSourcesRequest,
    HydratedSources,
    Target,
    Targets,
)
from pants.util.logging import LogLevel

from pack_metadata.target_types import (
    PackContentResourceSourceField,
    PackContentResourceTypeField,
    PackContentResourceTypes,
    PackMetadata,
)


@dataclass(frozen=True)
class PackContentResourceTargetsOfTypeRequest:
    types: tuple[PackContentResourceTypes, ...]


class PackContentResourceTargetsOfType(Targets):
    pass


@rule(
    desc=f"Find all `{PackMetadata.alias}` targets in project filtered by content type",
    level=LogLevel.DEBUG,
)
async def find_pack_metadata_targets_of_types(
    request: PackContentResourceTargetsOfTypeRequest, targets: AllTargets
) -> PackContentResourceTargetsOfType:
    return PackContentResourceTargetsOfType(
        tgt
        for tgt in targets
        if tgt.has_field(PackContentResourceSourceField)
        and (
            not request.types
            or tgt[PackContentResourceTypeField].value in request.types
        )
    )


@dataclass(frozen=True)
class PackContentPythonEntryPoint:
    metadata_address: Address
    content_type: PackContentResourceTypes
    entry_point: str
    python_address: Address
    resolve: str
    module: str


class PackContentPythonEntryPoints(Collection[PackContentPythonEntryPoint]):
    pass


class PackContentPythonEntryPointsRequest:
    pass


def get_possible_modules(path: PurePath) -> list[str]:
    module = path.stem if path.suffix == ".py" else path.name
    modules = [module]

    try:
        start = path.parent.parts.index("actions") + 1
    except ValueError:
        start = path.parent.parts.index("sensors") + 1

    # st2 adds the parent dir of the python file to sys.path at runtime.
    # by convention, however, just actions/ is on sys.path during tests.
    # so, also construct the module name from actions/ to support tests.
    if start < len(path.parent.parts):
        modules.append(".".join((*path.parent.parts[start:], module)))
    return modules


@rule(desc="Find all Pack Content entry_points that are python", level=LogLevel.DEBUG)
async def find_pack_content_python_entry_points(
    python_setup: PythonSetup, _: PackContentPythonEntryPointsRequest
) -> PackContentPythonEntryPoints:
    action_or_sensor = (
        PackContentResourceTypes.action_metadata,
        PackContentResourceTypes.sensor_metadata,
    )

    action_and_sensor_metadata_targets = await Get(
        PackContentResourceTargetsOfType,
        PackContentResourceTargetsOfTypeRequest(action_or_sensor),
    )
    action_and_sensor_metadata_sources = await MultiGet(
        Get(HydratedSources, HydrateSourcesRequest(tgt[PackContentResourceSourceField]))
        for tgt in action_and_sensor_metadata_targets
    )
    action_and_sensor_metadata_contents = await MultiGet(
        Get(DigestContents, Digest, source.snapshot.digest)
        for source in action_and_sensor_metadata_sources
    )

    # python file path -> list of info about metadata files that refer to it
    pack_content_entry_points_by_spec: DefaultDict[
        str, list[tuple[Address, PackContentResourceTypes, str]]
    ] = defaultdict(list)

    tgt: Target
    contents: DigestContents
    for tgt, contents in zip(
        action_and_sensor_metadata_targets, action_and_sensor_metadata_contents
    ):
        content_type = tgt[PackContentResourceTypeField].value
        if content_type not in action_or_sensor:
            continue
        assert len(contents) == 1
        try:
            metadata = yaml.safe_load(contents[0].content) or {}
        except yaml.YAMLError:
            continue
        if content_type == PackContentResourceTypes.action_metadata:
            runner_type = metadata.get("runner_type", "") or ""
            if runner_type != "python-script":
                # only python-script has special PYTHONPATH rules
                continue
        # get the entry_point to find subdirectory that contains the module
        entry_point = metadata.get("entry_point", "") or ""
        if entry_point:
            # address.filename is basically f"{spec_path}/{relative_file_path}"
            path = PurePath(tgt.address.filename).parent / entry_point
            pack_content_entry_points_by_spec[str(path)].append(
                (tgt.address, content_type, entry_point)
            )

    python_targets = await Get(
        Targets,
        RawSpecs(
            file_literals=tuple(
                FileLiteralSpec(spec_path)
                for spec_path in pack_content_entry_points_by_spec
            ),
            unmatched_glob_behavior=GlobMatchErrorBehavior.ignore,
            description_of_origin="pack_metadata python module mapper",
        ),
    )

    pack_content_entry_points: list[PackContentPythonEntryPoint] = []
    for tgt in python_targets:
        if not tgt.has_field(PythonResolveField):
            # this is unexpected
            continue
        for (
            metadata_address,
            content_type,
            entry_point,
        ) in pack_content_entry_points_by_spec[tgt.address.filename]:
            resolve = tgt[PythonResolveField].normalized_value(python_setup)

            for module in get_possible_modules(PurePath(tgt.address.filename)):
                pack_content_entry_points.append(
                    PackContentPythonEntryPoint(
                        metadata_address=metadata_address,
                        content_type=content_type,
                        entry_point=entry_point,
                        python_address=tgt.address,
                        resolve=resolve,
                        module=module,
                    )
                )

    return PackContentPythonEntryPoints(pack_content_entry_points)


def rules():
    return (*collect_rules(),)
