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

import pytest

from pants.backend.python import target_types_rules
from pants.backend.python.target_types import PythonSourcesGeneratorTarget

from pants.core.util_rules.source_files import SourceFiles, SourceFilesRequest
from pants.engine.addresses import Address
from pants.engine.fs import CreateDigest, Digest, FileContent, Snapshot
from pants.engine.target import Target
from pants.core.goals.fmt import FmtResult
from pants.core.util_rules.partitions import Partitions
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .rules import (
    GenerateSchemasFieldSet,
    GenerateSchemasViaFmtTargetsRequest,
    rules as schemas_rules,
)
from .subsystem import GenerateSchemas
from .target_types import Schemas


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *schemas_rules(),
            *target_types_rules.rules(),
            QueryRule(
                Partitions, (GenerateSchemasViaFmtTargetsRequest.PartitionRequest,)
            ),
            QueryRule(FmtResult, (GenerateSchemasViaFmtTargetsRequest.Batch,)),
            QueryRule(SourceFiles, (SourceFilesRequest,)),
        ],
        target_types=[Schemas, PythonSourcesGeneratorTarget],
    )


def run_st2_generate_schemas(
    rule_runner: RuleRunner,
    targets: list[Target],
    *,
    extra_args: list[str] | None = None,
) -> FmtResult:
    rule_runner.set_options(
        [
            "--backend-packages=schemas",
            f"--source-root-patterns=/{GenerateSchemas.source_root}",
            *(extra_args or ()),
        ],
        env_inherit={"PATH", "PYENV_ROOT", "HOME"},
    )
    field_sets = tuple(GenerateSchemasFieldSet.create(tgt) for tgt in targets)
    input_sources = rule_runner.request(
        SourceFiles,
        [
            SourceFilesRequest(field_set.sources for field_set in field_sets),
        ],
    )

    # run generate_schemas_partitioner rule
    partitions = rule_runner.request(
        Partitions,
        [GenerateSchemasViaFmtTargetsRequest.PartitionRequest(field_sets)],
    )
    assert len(partitions) == 1

    # run generate_schemas_via_fmt rule
    fmt_result = rule_runner.request(
        FmtResult,
        [
            GenerateSchemasViaFmtTargetsRequest.Batch(
                tool_name="",
                elements=partitions[0].elements,  # ie: files
                partition_metadata=partitions[0].metadata,
                snapshot=input_sources.snapshot,
            ),
        ],
    )
    return fmt_result


# copied from pantsbuild/pants.git/src/python/pants/backend/python/lint/black/rules_integration_test.py
def get_snapshot(rule_runner: RuleRunner, source_files: dict[str, str]) -> Snapshot:
    files = [
        FileContent(path, content.encode()) for path, content in source_files.items()
    ]
    digest = rule_runner.request(Digest, [CreateDigest(files)])
    return rule_runner.request(Snapshot, [digest])


# add dummy script at st2common/st2common/cmd/generate_schemas.py that the test can load.
GENERATE_SCHEMAS_PY = """
import os


def main():
    print('Generated schema for the "dummy" model.')
    schema_text = "{schema_text}"
    schema_file = os.path.join("{schemas_dir}", "dummy.json")
    print('Schema will be written to "%s".' % schema_file)
    with open(schema_file, "w") as f:
        f.write(schema_text)
"""


def write_files(
    schemas_dir: str, schema_file: str, before: str, after: str, rule_runner: RuleRunner
) -> None:
    files = {
        f"{schemas_dir}/{schema_file}": before,
        f"{schemas_dir}/BUILD": "schemas(name='t')",
        # add in the target that's hard-coded in the generate_schemas_via_fmt rue
        f"{GenerateSchemas.directory}/{GenerateSchemas.cmd}.py": GENERATE_SCHEMAS_PY.format(
            schemas_dir=schemas_dir, schema_text=after
        ),
        f"{GenerateSchemas.directory}/BUILD": "python_sources()",
    }

    module = GenerateSchemas.directory
    while module != GenerateSchemas.source_root:
        files[f"{module}/__init__.py"] = ""
        module = os.path.dirname(module)

    rule_runner.write_files(files)


def test_changed(rule_runner: RuleRunner) -> None:
    write_files(
        schemas_dir="my_dir",
        schema_file="dummy.json",
        before="BEFORE",
        after="AFTER",
        rule_runner=rule_runner,
    )

    tgt = rule_runner.get_target(
        Address("my_dir", target_name="t", relative_file_path="dummy.json")
    )
    fmt_result = run_st2_generate_schemas(rule_runner, [tgt])
    assert 'Schema will be written to "my_dir/dummy.json".' in fmt_result.stdout
    assert fmt_result.output == get_snapshot(
        rule_runner, {"my_dir/dummy.json": "AFTER"}
    )
    assert fmt_result.did_change is True


def test_unchanged(rule_runner: RuleRunner) -> None:
    write_files(
        schemas_dir="my_dir",
        schema_file="dummy.json",
        before="AFTER",
        after="AFTER",
        rule_runner=rule_runner,
    )

    tgt = rule_runner.get_target(
        Address("my_dir", target_name="t", relative_file_path="dummy.json")
    )
    fmt_result = run_st2_generate_schemas(rule_runner, [tgt])
    assert 'Schema will be written to "my_dir/dummy.json".' in fmt_result.stdout
    assert fmt_result.output == get_snapshot(
        rule_runner, {"my_dir/dummy.json": "AFTER"}
    )
    assert fmt_result.did_change is False
