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
from pants.core.util_rules.partitions import PartitionerType
from pants.engine.fs import (
    CreateDigest,
    Digest,
    FileContent,
    Snapshot,
)
from pants.engine.process import ProcessResult
from pants.engine.rules import Get, collect_rules, rule
from pants.engine.target import FieldSet
from pants.util.logging import LogLevel
from pants.util.strutil import strip_v2_chroot_path

from sample_conf.subsystem import ConfigGen
from sample_conf.target_types import SampleConfSourceField


@dataclass(frozen=True)
class GenerateSampleConfFieldSet(FieldSet):
    required_fields = (SampleConfSourceField,)

    source: SampleConfSourceField


class GenerateSampleConfViaFmtTargetsRequest(FmtTargetsRequest):
    field_set_type = GenerateSampleConfFieldSet
    tool_subsystem = ConfigGen
    partitioner_type = PartitionerType.DEFAULT_SINGLE_PARTITION


@rule(
    desc=f"Update conf/st2.conf.sample with {ConfigGen.directory}/{ConfigGen.script}.py",
    level=LogLevel.DEBUG,
)
async def generate_sample_conf_via_fmt(
    request: GenerateSampleConfViaFmtTargetsRequest.Batch,
    subsystem: ConfigGen,
) -> FmtResult:
    # We use a pex to actually generate the sample conf with an external script.
    # Generation cannot be inlined here because it needs to import the st2 code.
    # (the script location is defined on the ConfigGen subsystem)
    pex = await Get(VenvPex, PexFromTargetsRequest, subsystem.pex_request())

    result = await Get(
        ProcessResult,
        VenvPexProcess(
            pex,
            description="Regenerating st2.conf.sample",
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


def rules():
    return [
        *collect_rules(),
        *GenerateSampleConfViaFmtTargetsRequest.rules(),
        *pex.rules(),
        *pex_from_targets.rules(),
    ]
