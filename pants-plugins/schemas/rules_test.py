# Copyright 2022 The StackStorm Authors.
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
from __future__ import annotations

import pytest

from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Address
from pants.engine.target import Target
from pants.core.goals.fmt import FmtResult
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .rules import GenerateSchemasFieldSet, GenerateSchemasViaFmtTargetsRequest, rules as schemas_rules
from .target_types import Schemas


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *schemas_rules(),
            QueryRule(FmtResult, (GenerateSchemasViaFmtTargetsRequest,)),
            QueryRule(SourceFiles, (SourceFilesRequest,)),
        ],
        target_types=[Schemas],
    )


def run_st2_generate_schemas(
    rule_runner: RuleRunner, targets: list[Target], *, extra_args: list[str] | None = None
) -> FmtResult:
    rule_runner.set_options(
        [
            "--backend-packages=schemas",
            *(extra_args or ()),
        ],
        env_inherit={"PATH", "PYENV_ROOT", "HOME"},
    )
    field_sets = [GenerateSchemasFieldSet.create(tgt) for tgt in targets]
    input_sources = rule_runner.request(
        SourceFiles,
        [
            SourceFilesRequest(field_set.sources for field_set in field_sets),
        ],
    )
    fmt_result = rule_runner.request(
        FmtResult,
        [
            GenerateSchemasViaFmtTargetsRequest(field_sets, snapshot=input_sources.snapshot),
        ],
    )
    return results.results


# copied from pantsbuild/pants.git/src/python/pants/backend/python/lint/black/rules_integration_test.py
def get_snapshot(rule_runner: RuleRunner, source_files: dict[str, str]) -> Snapshot:
    files = [FileContent(path, content.encode()) for path, content in source_files.items()]
    digest = rule_runner.request(Digest, [CreateDigest(files)])
    return rule_runner.request(Snapshot, [digest])


def test_something(rule_runner: RuleRunner) -> None:
    rule_runner.write_files({"action.json": "{}", "BUILD": "schemas(name='t')"})
    tgt = rule_runner.get_target(Address("", target_name="t", relative_file_path="action.json"))
    fmt_result = run_st2_generate_schemas(rule_runner, [tgt])
    # TODO: add asserts
