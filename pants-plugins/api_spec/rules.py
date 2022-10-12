# Copyright 2021 The StackStorm Authors.
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

from pants.backend.python.target_types import EntryPoint
from pants.backend.python.util_rules.pex import (
    VenvPex,
    VenvPexProcess,
)
from pants.backend.python.util_rules.pex_from_targets import PexFromTargetsRequest
from pants.core.goals.fmt import FmtResult, FmtTargetsRequest
from pants.core.goals.lint import LintResult, LintResults, LintTargetsRequest
from pants.core.target_types import FileSourceField, ResourceSourceField
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Address
from pants.engine.fs import (
    CreateDigest,
    Digest,
    FileContent,
    MergeDigests,
    Snapshot,
)
from pants.engine.process import FallibleProcessResult, ProcessResult
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import (
    FieldSet,
    SourcesField,
    TransitiveTargets,
    TransitiveTargetsRequest,
)
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel

from api_spec.target_types import APISpecSourceField


GENERATE_SCRIPT = "generate_api_spec"
VALIDATE_SCRIPT = "validate_api_spec"

SPEC_HEADER = b"""\
# NOTE: This file is auto-generated - DO NOT EDIT MANUALLY
# Edit st2common/st2common/openapi.yaml.j2 and then run
# ./pants fmt st2common/st2common/openapi.yaml
# to generate the final spec file
"""


@dataclass(frozen=True)
class APISpecFieldSet(FieldSet):
    required_fields = (APISpecSourceField,)

    source: APISpecSourceField


class GenerateAPISpecViaFmtTargetsRequest(FmtTargetsRequest):
    field_set_type = APISpecFieldSet
    name = GENERATE_SCRIPT


class ValidateAPISpecRequest(LintTargetsRequest):
    field_set_type = APISpecFieldSet
    name = VALIDATE_SCRIPT


@rule(
    desc="Update openapi.yaml with st2-generate-api-spec",
    level=LogLevel.DEBUG,
)
async def generate_api_spec_via_fmt(
    request: GenerateAPISpecViaFmtTargetsRequest,
) -> FmtResult:
    # There will only be one target+field_set, but we iterate
    # to satisfy how fmt expects that there could be more than one.
    # If there is more than one, they will all get the same contents.

    # Find all the dependencies of our target
    transitive_targets = await Get(
        TransitiveTargets,
        TransitiveTargetsRequest(
            [field_set.address for field_set in request.field_sets]
        ),
    )

    dependency_files_get = Get(
        SourceFiles,
        SourceFilesRequest(
            sources_fields=[
                tgt.get(SourcesField) for tgt in transitive_targets.dependencies
            ],
            for_sources_types=(FileSourceField, ResourceSourceField),
            # enable_codegen=True,
        ),
    )

    source_files_get = Get(
        SourceFiles,
        SourceFilesRequest(field_set.source for field_set in request.field_sets),
    )

    # actually generate it with an external script.
    # Generation cannot be inlined here because it needs to import the st2 code.
    pex_get = Get(
        VenvPex,
        PexFromTargetsRequest(
            [
                Address(
                    "st2common/st2common/cmd",
                    target_name="cmd",
                    relative_file_path=f"{GENERATE_SCRIPT}.py",
                ),
            ],
            output_filename=f"{GENERATE_SCRIPT}.pex",
            internal_only=True,
            main=EntryPoint.parse(f"st2common.cmd.{GENERATE_SCRIPT}:main"),
        ),
    )

    pex, dependency_files, source_files = await MultiGet(
        pex_get, dependency_files_get, source_files_get
    )

    # If we were given an input digest from a previous formatter for the source files, then we
    # should use that input digest instead of the one we read from the filesystem.
    source_files_snapshot = (
        source_files.snapshot if request.snapshot is None else request.snapshot
    )

    input_digest = await Get(
        Digest,
        MergeDigests((dependency_files.snapshot.digest, source_files_snapshot.digest)),
    )

    result = await Get(
        ProcessResult,
        VenvPexProcess(
            pex,
            argv=(
                "--config-file",
                "conf/st2.dev.conf",
            ),
            input_digest=input_digest,
            description="Regenerating openapi.yaml api spec",
            level=LogLevel.DEBUG,
        ),
    )

    contents = [
        FileContent(
            f"{field_set.address.spec_path}/{field_set.source.value}",
            SPEC_HEADER + result.stdout,
        )
        for field_set in request.field_sets
    ]

    output_digest = await Get(Digest, CreateDigest(contents))
    output_snapshot = await Get(Snapshot, Digest, output_digest)
    return FmtResult.create(request, result, output_snapshot, strip_chroot_path=True)


@rule(
    desc="Validate openapi.yaml with st2-validate-api-spec",
    level=LogLevel.DEBUG,
)
async def validate_api_spec(
    request: ValidateAPISpecRequest,
) -> LintResults:
    # There will only be one target+field_set, but we iterate
    # to satisfy how lint expects that there could be more than one.
    # If there is more than one, they will all get the same contents.

    # Find all the dependencies of our target
    transitive_targets = await Get(
        TransitiveTargets,
        TransitiveTargetsRequest(
            [field_set.address for field_set in request.field_sets]
        ),
    )

    dependency_files_get = Get(
        SourceFiles,
        SourceFilesRequest(
            sources_fields=[
                tgt.get(SourcesField) for tgt in transitive_targets.dependencies
            ],
            for_sources_types=(FileSourceField, ResourceSourceField),
            # enable_codegen=True,
        ),
    )

    source_files_get = Get(
        SourceFiles,
        SourceFilesRequest(field_set.source for field_set in request.field_sets),
    )

    # actually validate it with an external script.
    # Validation cannot be inlined here because it needs to import the st2 code.
    pex_get = Get(
        VenvPex,
        PexFromTargetsRequest(
            [
                Address(
                    "st2common/st2common/cmd",
                    target_name="cmd",
                    relative_file_path=f"{VALIDATE_SCRIPT}.py",
                ),
            ],
            output_filename=f"{VALIDATE_SCRIPT}.pex",
            internal_only=True,
            main=EntryPoint.parse(f"st2common.cmd.{VALIDATE_SCRIPT}:main"),
        ),
    )

    pex, dependency_files, source_files = await MultiGet(
        pex_get, dependency_files_get, source_files_get
    )

    input_digest = await Get(
        Digest,
        MergeDigests((dependency_files.snapshot.digest, source_files.snapshot.digest)),
    )

    process_result = await Get(
        FallibleProcessResult,
        VenvPexProcess(
            pex,
            argv=(
                "--config-file",
                "conf/st2.dev.conf",
                # "--validate-defs",  # check for x-api-model in definitions
                # "--verbose",  # show definitions on failure
            ),
            input_digest=input_digest,
            description="Validating openapi.yaml api spec",
            level=LogLevel.DEBUG,
        ),
    )

    result = LintResult.from_fallible_process_result(process_result)
    return LintResults([result], linter_name=request.name)


def rules():
    return [
        *collect_rules(),
        UnionRule(FmtTargetsRequest, GenerateAPISpecViaFmtTargetsRequest),
        UnionRule(LintTargetsRequest, ValidateAPISpecRequest),
    ]
