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
import os
from dataclasses import dataclass

from pants.backend.python.util_rules import pex, pex_from_targets
from pants.backend.python.util_rules.pex import (
    VenvPex,
    VenvPexProcess,
)
from pants.backend.python.util_rules.pex_from_targets import PexFromTargetsRequest
from pants.core.goals.fmt import FmtResult, FmtTargetsRequest
from pants.core.util_rules.partitions import PartitionerType
from pants.engine.fs import MergeDigests, Snapshot
from pants.engine.process import FallibleProcessResult
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import FieldSet
from pants.util.logging import LogLevel
from pants.util.strutil import strip_v2_chroot_path

from schemas.subsystem import GenerateSchemas
from schemas.target_types import SchemasSourcesField


@dataclass(frozen=True)
class GenerateSchemasFieldSet(FieldSet):
    required_fields = (SchemasSourcesField,)

    sources: SchemasSourcesField


class GenerateSchemasViaFmtTargetsRequest(FmtTargetsRequest):
    field_set_type = GenerateSchemasFieldSet
    tool_subsystem = GenerateSchemas
    partitioner_type = PartitionerType.DEFAULT_SINGLE_PARTITION


@rule(
    desc="Update contrib/schemas/*.json with st2-generate-schemas",
    level=LogLevel.DEBUG,
)
async def generate_schemas_via_fmt(
    request: GenerateSchemasViaFmtTargetsRequest.Batch,
    subsystem: GenerateSchemas,
) -> FmtResult:
    # We use a pex to actually generate the schemas with an external script.
    # Generation cannot be inlined here because it needs to import the st2 code.
    # (the script location is defined on the GenerateSchemas subsystem)
    pex = await Get(VenvPex, PexFromTargetsRequest, subsystem.pex_request())

    # There will probably only be one target+field_set, and therefor only one directory
    output_directories = {os.path.dirname(f) for f in request.files}

    results = await MultiGet(
        Get(
            FallibleProcessResult,
            VenvPexProcess(
                pex,
                argv=(output_directory,),
                # This script actually ignores the input files.
                input_digest=request.snapshot.digest,
                output_directories=[output_directory],
                description=f"Regenerating st2 metadata schemas in {output_directory}",
                level=LogLevel.DEBUG,
            ),
        )
        for output_directory in output_directories
    )

    output_snapshot = await Get(
        Snapshot, MergeDigests(result.output_digest for result in results)
    )

    stdout = "\n".join(
        [strip_v2_chroot_path(process_result.stdout) for process_result in results]
    )
    stderr = "\n".join(
        [strip_v2_chroot_path(process_result.stderr) for process_result in results]
    )
    return FmtResult(
        input=request.snapshot,
        output=output_snapshot,
        stdout=stdout,
        stderr=stderr,
        tool_name=request.tool_name,
    )


def rules():
    return [
        *collect_rules(),
        *GenerateSchemasViaFmtTargetsRequest.rules(),
        *pex.rules(),
        *pex_from_targets.rules(),
    ]
