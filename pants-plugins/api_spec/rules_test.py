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
from __future__ import annotations

import os

from typing import Sequence

import pytest

from pants.backend.python import target_types_rules
from pants.backend.python.target_types import PythonSourcesGeneratorTarget

from pants.core.util_rules.config_files import rules as config_files_rules
from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Address
from pants.engine.fs import CreateDigest, Digest, EMPTY_DIGEST, FileContent, Snapshot
from pants.engine.target import Target
from pants.core.goals.fmt import FmtResult
from pants.core.goals.lint import LintResult
from pants.core.util_rules.partitions import Partitions
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .rules import (
    APISpecFieldSet,
    GenerateAPISpecViaFmtTargetsRequest,
    ValidateAPISpecRequest,
    rules as api_spec_rules,
)
from .subsystem import GenerateApiSpec, ValidateApiSpec
from .target_types import APISpec


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *api_spec_rules(),
            *target_types_rules.rules(),
            *config_files_rules(),
            # generate
            QueryRule(
                Partitions, (GenerateAPISpecViaFmtTargetsRequest.PartitionRequest,)
            ),
            QueryRule(FmtResult, (GenerateAPISpecViaFmtTargetsRequest.Batch,)),
            # validate
            QueryRule(Partitions, (ValidateAPISpecRequest.PartitionRequest,)),
            QueryRule(LintResult, (ValidateAPISpecRequest.Batch,)),
            # etc
            QueryRule(SourceFiles, (SourceFilesRequest,)),
        ],
        target_types=[APISpec, PythonSourcesGeneratorTarget],
    )


def run_st2_generate_api_spec(
    rule_runner: RuleRunner,
    targets: list[Target],
    *,
    extra_args: list[str] | None = None,
) -> FmtResult:
    rule_runner.set_options(
        [
            "--backend-packages=api_spec",
            f"--source-root-patterns=/{GenerateApiSpec.source_root}",
            *(extra_args or ()),
        ],
        env_inherit={"PATH", "PYENV_ROOT", "HOME"},
    )
    field_sets = tuple(APISpecFieldSet.create(tgt) for tgt in targets)
    input_sources = rule_runner.request(
        SourceFiles,
        [
            SourceFilesRequest(field_set.source for field_set in field_sets),
        ],
    )

    # run generate_api_spec_partitioner rule
    partitions = rule_runner.request(
        Partitions,
        [GenerateAPISpecViaFmtTargetsRequest.PartitionRequest(field_sets)],
    )
    assert len(partitions) == 1

    # run generate_api_spec_via_fmt rule
    fmt_result = rule_runner.request(
        FmtResult,
        [
            GenerateAPISpecViaFmtTargetsRequest.Batch(
                tool_name="",
                elements=partitions[0].elements,  # ie: files
                partition_metadata=partitions[0].metadata,
                snapshot=input_sources.snapshot,
            ),
        ],
    )
    return fmt_result


def run_st2_validate_api_spec(
    rule_runner: RuleRunner,
    targets: list[Target],
    *,
    extra_args: list[str] | None = None,
) -> Sequence[LintResult]:
    rule_runner.set_options(
        [
            "--backend-packages=api_spec",
            f"--source-root-patterns=/{ValidateApiSpec.source_root}",
            *(extra_args or ()),
        ],
        env_inherit={"PATH", "PYENV_ROOT", "HOME"},
    )
    field_sets = tuple(APISpecFieldSet.create(tgt) for tgt in targets)

    # run validate_api_spec_partitioner rule
    partitions = rule_runner.request(
        Partitions,
        [ValidateAPISpecRequest.PartitionRequest(field_sets)],
    )
    assert len(partitions) == 1

    # run validate_api_spec_via_fmt rule
    lint_result = rule_runner.request(
        LintResult,
        [
            ValidateAPISpecRequest.Batch(
                tool_name="",
                elements=partitions[0].elements,  # ie: field_sets
                partition_metadata=partitions[0].metadata,
            ),
        ],
    )
    return lint_result


# copied from pantsbuild/pants.git/src/python/pants/backend/python/lint/black/rules_integration_test.py
def get_snapshot(rule_runner: RuleRunner, source_files: dict[str, str]) -> Snapshot:
    files = [
        FileContent(path, content.encode()) for path, content in source_files.items()
    ]
    digest = rule_runner.request(Digest, [CreateDigest(files)])
    return rule_runner.request(Snapshot, [digest])


# add dummy script at st2common/st2common/cmd/generate_api_spec.py that the test can load.
GENERATE_API_SPEC_PY = """
import os


def main():
    api_spec_text = "{api_spec_text}"
    print(api_spec_text)
"""


def write_generate_files(
    api_spec_dir: str,
    api_spec_file: str,
    before: str,
    after: str,
    rule_runner: RuleRunner,
) -> None:
    files = {
        f"{api_spec_dir}/{api_spec_file}": before,
        f"{api_spec_dir}/BUILD": f"api_spec(name='t', source='{api_spec_file}')",
        # add in the target that's hard-coded in the generate_api_spec_via_fmt rule
        f"{GenerateApiSpec.directory}/{GenerateApiSpec.cmd}.py": GENERATE_API_SPEC_PY.format(
            api_spec_dir=api_spec_dir, api_spec_text=after
        ),
        f"{GenerateApiSpec.directory}/BUILD": "python_sources()",
        GenerateApiSpec.config_file: "",
    }

    module = GenerateApiSpec.directory
    while module != GenerateApiSpec.source_root:
        files[f"{module}/__init__.py"] = ""
        module = os.path.dirname(module)

    rule_runner.write_files(files)


def test_generate_changed(rule_runner: RuleRunner) -> None:
    write_generate_files(
        api_spec_dir="my_dir",
        api_spec_file="dummy.yaml",
        before="BEFORE",
        after="AFTER",
        rule_runner=rule_runner,
    )

    tgt = rule_runner.get_target(
        Address("my_dir", target_name="t", relative_file_path="dummy.yaml")
    )
    fmt_result = run_st2_generate_api_spec(rule_runner, [tgt])
    assert fmt_result.output == get_snapshot(
        rule_runner, {"my_dir/dummy.yaml": "AFTER\n"}
    )
    assert fmt_result.did_change is True


def test_generate_unchanged(rule_runner: RuleRunner) -> None:
    write_generate_files(
        api_spec_dir="my_dir",
        api_spec_file="dummy.yaml",
        before="AFTER\n",
        after="AFTER",  # print() adds a newline
        rule_runner=rule_runner,
    )

    tgt = rule_runner.get_target(
        Address("my_dir", target_name="t", relative_file_path="dummy.yaml")
    )
    fmt_result = run_st2_generate_api_spec(rule_runner, [tgt])
    assert fmt_result.output == get_snapshot(
        rule_runner, {"my_dir/dummy.yaml": "AFTER\n"}
    )
    assert fmt_result.did_change is False


# add dummy script at st2common/st2common/cmd/validate_api_spec.py that the test can load.
VALIDATE_API_SPEC_PY = """
import sys


def main():
    sys.exit({rc})
"""


def write_validate_files(
    api_spec_dir: str,
    api_spec_file: str,
    contents: str,
    rc: int,
    rule_runner: RuleRunner,
) -> None:
    files = {
        f"{api_spec_dir}/{api_spec_file}": contents,
        f"{api_spec_dir}/BUILD": f"api_spec(name='t', source='{api_spec_file}')",
        # add in the target that's hard-coded in the generate_api_spec_via_fmt rule
        f"{ValidateApiSpec.directory}/{ValidateApiSpec.cmd}.py": VALIDATE_API_SPEC_PY.format(
            api_spec_dir=api_spec_dir, rc=rc
        ),
        f"{ValidateApiSpec.directory}/BUILD": "python_sources()",
        ValidateApiSpec.config_file: "",
    }

    module = ValidateApiSpec.directory
    while module != ValidateApiSpec.source_root:
        files[f"{module}/__init__.py"] = ""
        module = os.path.dirname(module)

    rule_runner.write_files(files)


def test_validate_passed(rule_runner: RuleRunner) -> None:
    write_validate_files(
        api_spec_dir="my_dir",
        api_spec_file="dummy.yaml",
        contents="PASS",
        rc=0,
        rule_runner=rule_runner,
    )

    tgt = rule_runner.get_target(
        Address("my_dir", target_name="t", relative_file_path="dummy.yaml")
    )
    lint_result = run_st2_validate_api_spec(rule_runner, [tgt])
    assert lint_result.exit_code == 0
    assert lint_result.report == EMPTY_DIGEST


def test_validate_failed(rule_runner: RuleRunner) -> None:
    write_validate_files(
        api_spec_dir="my_dir",
        api_spec_file="dummy.yaml",
        contents="FAIL",
        rc=1,
        rule_runner=rule_runner,
    )

    tgt = rule_runner.get_target(
        Address("my_dir", target_name="t", relative_file_path="dummy.yaml")
    )
    lint_result = run_st2_validate_api_spec(rule_runner, [tgt])
    assert lint_result.exit_code == 1
    assert lint_result.report == EMPTY_DIGEST
