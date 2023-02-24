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

from pants.backend.python.target_types import EntryPoint
from pants.backend.python.util_rules import pex, pex_from_targets
from pants.backend.python.util_rules.pex import (
    VenvPex,
    VenvPexProcess,
)
from pants.backend.python.util_rules.pex_from_targets import PexFromTargetsRequest
from pants.core.goals.fmt import FmtResult, FmtTargetsRequest
from pants.engine.addresses import Address
from pants.engine.fs import MergeDigests, Snapshot
from pants.engine.process import FallibleProcessResult
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import FieldSet
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel
from pants.util.strutil import strip_v2_chroot_path

from schemas.target_types import SchemasSourcesField


# these constants are also used in the tests.
CMD_SOURCE_ROOT = "st2common"
CMD_DIR = "st2common/st2common/cmd"
CMD_MODULE = "st2common.cmd"
CMD = "generate_schemas"


@dataclass(frozen=True)
class GenerateSchemasFieldSet(FieldSet):
    required_fields = (SchemasSourcesField,)

    sources: SchemasSourcesField


class GenerateSchemasViaFmtTargetsRequest(FmtTargetsRequest):
    field_set_type = GenerateSchemasFieldSet
    name = CMD


@rule(
    desc="Update contrib/schemas/*.json with st2-generate-schemas",
    level=LogLevel.DEBUG,
)
async def generate_schemas_via_fmt(
    request: GenerateSchemasViaFmtTargetsRequest,
) -> FmtResult:
    # We use a pex to actually generate the schemas with an external script.
    # Generation cannot be inlined here because it needs to import the st2 code.
    pex = await Get(
        VenvPex,
        PexFromTargetsRequest(
            [
                Address(
                    CMD_DIR,
                    target_name="cmd",
                    relative_file_path=f"{CMD}.py",
                )
            ],
            output_filename=f"{CMD}.pex",
            internal_only=True,
            main=EntryPoint.parse(f"{CMD_MODULE}.{CMD}:main"),
        ),
    )

    # There will probably only be one target+field_set, but we iterate
    # to satisfy how fmt expects that there could be more than one.
    output_directories = [fs.address.spec_path for fs in request.field_sets]

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
        formatter_name=request.name,
    )


def rules():
    return [
        *collect_rules(),
        UnionRule(FmtTargetsRequest, GenerateSchemasViaFmtTargetsRequest),
        *pex.rules(),
        *pex_from_targets.rules(),
    ]
