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
from dataclasses import dataclass

from pants.backend.python.util_rules import pex, pex_from_targets
from pants.backend.python.util_rules.pex import (
    VenvPex,
    VenvPexProcess,
)
from pants.backend.python.util_rules.pex_from_targets import PexFromTargetsRequest
from pants.core.goals.fmt import FmtResult, FmtTargetsRequest
from pants.core.goals.lint import LintResult, LintTargetsRequest
from pants.core.util_rules.config_files import ConfigFiles, ConfigFilesRequest
from pants.core.util_rules.partitions import PartitionerType
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.fs import (
    CreateDigest,
    Digest,
    FileContent,
    MergeDigests,
    Snapshot,
)
from pants.engine.process import FallibleProcessResult, ProcessResult
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import FieldSet
from pants.util.logging import LogLevel
from pants.util.strutil import strip_v2_chroot_path

from api_spec.subsystem import GenerateApiSpec, ValidateApiSpec
from api_spec.target_types import APISpecSourceField


@dataclass(frozen=True)
class APISpecFieldSet(FieldSet):
    required_fields = (APISpecSourceField,)

    source: APISpecSourceField


class GenerateAPISpecViaFmtTargetsRequest(FmtTargetsRequest):
    field_set_type = APISpecFieldSet
    tool_subsystem = GenerateApiSpec
    partitioner_type = PartitionerType.DEFAULT_SINGLE_PARTITION


class ValidateAPISpecRequest(LintTargetsRequest):
    field_set_type = APISpecFieldSet
    tool_subsystem = ValidateApiSpec
    partitioner_type = PartitionerType.DEFAULT_SINGLE_PARTITION


@rule(
    desc="Update openapi.yaml with st2-generate-api-spec",
    level=LogLevel.DEBUG,
)
async def generate_api_spec_via_fmt(
    request: GenerateAPISpecViaFmtTargetsRequest.Batch,
    subsystem: GenerateApiSpec,
) -> FmtResult:
    config_files_get = Get(ConfigFiles, ConfigFilesRequest, subsystem.config_request())

    # We use a pex to actually generate the api spec with an external script.
    # Generation cannot be inlined here because it needs to import the st2 code.
    # (the script location is defined on the GenerateApiSpec subsystem)
    pex_get = Get(VenvPex, PexFromTargetsRequest, subsystem.pex_request())

    config_files, pex = await MultiGet(config_files_get, pex_get)

    input_digest = await Get(
        Digest,
        MergeDigests((config_files.snapshot.digest, request.snapshot.digest)),
    )

    result = await Get(
        ProcessResult,
        VenvPexProcess(
            pex,
            argv=(
                "--config-file",
                subsystem.config_file,
            ),
            input_digest=input_digest,
            description="Regenerating openapi.yaml api spec",
            level=LogLevel.DEBUG,
        ),
    )

    contents = [FileContent(file, result.stdout) for file in request.files]

    output_digest = await Get(Digest, CreateDigest(contents))
    output_snapshot = await Get(Snapshot, Digest, output_digest)

    return FmtResult(
        input=request.snapshot,
        output=output_snapshot,
        # Drop result.stdout since we already wrote it to a file
        stdout="",
        stderr=strip_v2_chroot_path(result.stderr),
        tool_name=request.tool_name,
    )


@rule(
    desc="Validate openapi.yaml with st2-validate-api-spec",
    level=LogLevel.DEBUG,
)
async def validate_api_spec(
    request: ValidateAPISpecRequest.Batch,
    subsystem: ValidateApiSpec,
) -> LintResult:
    source_files_get = Get(
        SourceFiles,
        SourceFilesRequest(field_set.source for field_set in request.elements),
    )

    config_files_get = Get(ConfigFiles, ConfigFilesRequest, subsystem.config_request())

    # We use a pex to actually validate the api spec with an external script.
    # Validation cannot be inlined here because it needs to import the st2 code.
    # (the script location is defined on the ValidateApiSpec subsystem)
    pex_get = Get(VenvPex, PexFromTargetsRequest, subsystem.pex_request())

    source_files, config_files, pex = await MultiGet(
        source_files_get, config_files_get, pex_get
    )

    input_digest = await Get(
        Digest,
        MergeDigests((config_files.snapshot.digest, source_files.snapshot.digest)),
    )

    process_result = await Get(
        FallibleProcessResult,
        VenvPexProcess(
            pex,
            argv=(
                "--config-file",
                subsystem.config_file,
                # TODO: Uncomment these as part of a project to fix the (many) issues it identifies.
                #       We can uncomment --validate-defs (and possibly --verbose) once the spec defs are valid.
                # "--validate-defs",  # check for x-api-model in definitions
                # "--verbose",  # show model definitions on failure (only applies to --validate-defs)
            ),
            input_digest=input_digest,
            description="Validating openapi.yaml api spec",
            level=LogLevel.DEBUG,
        ),
    )

    return LintResult.create(request, process_result)


def rules():
    return [
        *collect_rules(),
        *GenerateAPISpecViaFmtTargetsRequest.rules(),
        *ValidateAPISpecRequest.rules(),
        *pex.rules(),
        *pex_from_targets.rules(),
    ]
