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

from pants.backend.python.target_types import EntryPoint, PythonSourceField
from pants.backend.python.util_rules.pex import (
    Pex,
    PexRequest,
    VenvPex,
    VenvPexProcess,
)
from pants.backend.python.util_rules.pex_from_targets import PexFromTargetsRequest
from pants.backend.python.util_rules.python_sources import (
    PythonSourceFiles,
    PythonSourceFilesRequest,
)
from pants.core.goals.fmt import FmtResult, FmtRequest
from pants.core.goals.lint import LintResult, LintResults, LintTargetsRequest
from pants.core.target_types import FileSourceField
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Address, UnparsedAddressInputs
from pants.engine.fs import (
    CreateDigest,
    Digest,
    DigestContents,
    FileContent,
    MergeDigests,
    Snapshot,
)
from pants.engine.process import Process, ProcessResult
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import (
    FieldSet,
    GeneratedSources,
    GenerateSourcesRequest,
    SourcesField,
    Target,
    TransitiveTargets,
    TransitiveTargetsRequest,
)
from pants.engine.unions import UnionRule

from sample_conf.target_types import (
    SampleConfSourceField,
    SampleConf,
)


# CODEGEN #########################################################


class GenerateSampleConfRequest(GenerateSourcesRequest):
    input = SampleConfSourceField
    output = SampleConfSourceField


@rule
async def generate_sample_conf(
    request: GenerateSampleConfRequest,
) -> GeneratedSources:
    target = request.protocol_target

    # Find all the dependencies of our target
    transitive_targets = await Get(
        TransitiveTargets, TransitiveTargetsRequest([target.address])
    )

    # actually generate it with an external script.
    # Generation cannot be inlined here because it needs to import the st2 code.
    script = "config_gen"
    pex_get = Get(
        VenvPex,
        PexFromTargetsRequest(
            [Address("tools", target_name="tools", relative_file_path=f"{script}.py")],
            output_filename=f"{script}.pex",
            internal_only=True,
            main=EntryPoint(script),
        ),
    )
    sources_get = Get(
        PythonSourceFiles,
        PythonSourceFilesRequest(transitive_targets.closure, include_files=True),
    )
    pex, sources = await MultiGet(pex_get, sources_get)

    result = await Get(
        ProcessResult,
        VenvPexProcess(
            pex,
            description=f"Regenerating {request.protocol_target.address}.",
        ),
    )

    output_path = f"{target.address.spec_path}/{target[SampleConfSourceField].value}"
    content = FileContent(output_path, result.stdout)

    output_digest = await Get(Digest, CreateDigest([content]))
    output_snapshot = await Get(Snapshot, Digest, output_digest)
    return GeneratedSources(output_snapshot)


# FMT/LINT #########################################################


@dataclass(frozen=True)
class GenerateSampleConfFieldSet(FieldSet):
    required_fields = (SampleConfSourceField,)

    source: SampleConfSourceField


class GenerateSampleConfViaFmtRequest(FmtRequest, LintTargetsRequest):
    field_set_type = GenerateSampleConfFieldSet
    name = "st2.conf.sample"


@rule(desc="Generate st2.conf.sample")
async def gen_sample_conf_via_fmt(
    request: GenerateSampleConfViaFmtRequest,
) -> FmtResult:
    ...
    return FmtResult(..., formatter_name=request.name)


def rules():
    return [
        *collect_rules(),
        UnionRule(GenerateSourcesRequest, GenerateSampleConfRequest),
        UnionRule(FmtRequest, GenerateSampleConfViaFmtRequest),
        # UnionRule(LintTargetsRequest, GenerateSampleConfViaFmtRequest),
    ]
