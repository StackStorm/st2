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
from pants.engine.addresses import Address
from pants.engine.fs import (
    CreateDigest,
    Digest,
    FileContent,
    Snapshot,
)
from pants.engine.process import FallibleProcessResult
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.target import (
    FieldSet,
    SourcesField,
    TransitiveTargets,
    TransitiveTargetsRequest,
)
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel

from sample_conf.target_types import (
    SampleConfSourceField,
    SampleConf,
)


SCRIPT = "config_gen"


@dataclass(frozen=True)
class GenerateSampleConfFieldSet(FieldSet):
    required_fields = (SampleConfSourceField,)

    source: SampleConfSourceField


class GenerateSampleConfViaFmtRequest(FmtRequest):
    field_set_type = GenerateSampleConfFieldSet
    name = SCRIPT


@rule(
    desc="Update conf/st2.conf.sample with tools/config_gen.py",
    level=LogLevel.DEBUG,
)
async def generate_sample_conf_via_fmt(
    request: GenerateSampleConfViaFmtRequest,
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

    # actually generate it with an external script.
    # Generation cannot be inlined here because it needs to import the st2 code.
    pex = await Get(
        VenvPex,
        PexFromTargetsRequest(
            [Address("tools", target_name="tools", relative_file_path=f"{SCRIPT}.py")],
            output_filename=f"{SCRIPT}.pex",
            internal_only=True,
            main=EntryPoint(SCRIPT),
        ),
    )

    result = await Get(
        FallibleProcessResult,
        VenvPexProcess(
            pex,
            description=f"Regenerating st2.conf.sample",
        ),
    )

    contents = [
        FileContent(
            f"{field_set.address.spec_path}/{field_set.source.value}",
            result.stdout,
        )
        for field_set in request.field_sets
    ]

    output_digest = await Get(Digest, CreateDigest(contents))
    output_snapshot = await Get(Snapshot, Digest, output_digest)
    return FmtResult.create(request, result, output_snapshot, strip_chroot_path=True)


def rules():
    return [
        *collect_rules(),
        UnionRule(FmtRequest, GenerateSampleConfViaFmtRequest),
    ]
