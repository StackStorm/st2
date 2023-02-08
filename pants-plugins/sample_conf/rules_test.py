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
    GenerateSampleConfFieldSet,
    GenerateSampleConfViaFmtTargetsRequest,
    rules as sample_conf_rules,
)
from .subsystem import ConfigGen
from .target_types import SampleConf


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *sample_conf_rules(),
            *target_types_rules.rules(),
            QueryRule(
                Partitions, (GenerateSampleConfViaFmtTargetsRequest.PartitionRequest,)
            ),
            QueryRule(FmtResult, (GenerateSampleConfViaFmtTargetsRequest.Batch,)),
            QueryRule(SourceFiles, (SourceFilesRequest,)),
        ],
        target_types=[SampleConf, PythonSourcesGeneratorTarget],
    )


def run_st2_generate_sample_conf(
    rule_runner: RuleRunner,
    targets: list[Target],
    *,
    extra_args: list[str] | None = None,
) -> FmtResult:
    rule_runner.set_options(
        [
            "--backend-packages=sample_conf",
            f"--source-root-patterns=/{ConfigGen.directory}",
            *(extra_args or ()),
        ],
        env_inherit={"PATH", "PYENV_ROOT", "HOME"},
    )
    field_sets = tuple(GenerateSampleConfFieldSet.create(tgt) for tgt in targets)
    input_sources = rule_runner.request(
        SourceFiles,
        [
            SourceFilesRequest(field_set.source for field_set in field_sets),
        ],
    )

    # run DEFAULT_SINGLE_PARTITION rule
    partitions = rule_runner.request(
        Partitions,
        [GenerateSampleConfViaFmtTargetsRequest.PartitionRequest(field_sets)],
    )
    assert len(partitions) == 1

    # run generate_schemas_via_fmt rule
    fmt_result = rule_runner.request(
        FmtResult,
        [
            GenerateSampleConfViaFmtTargetsRequest.Batch(
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


# add dummy script at tools/config_gen.py that the test can load.
SCRIPT_PY = """
def main():
    sample_conf_text = "{sample_conf_text}"
    print(sample_conf_text)


if __name__ == "__main__":
    main()
"""


def write_files(
    sample_conf_dir: str,
    sample_conf_file: str,
    before: str,
    after: str,
    rule_runner: RuleRunner,
) -> None:
    files = {
        f"{sample_conf_dir}/{sample_conf_file}": before,
        f"{sample_conf_dir}/BUILD": f"sample_conf(name='t', source='{sample_conf_file}')",
        # add in the target that's hard-coded in the generate_sample_conf_via_fmt rue
        f"{ConfigGen.directory}/{ConfigGen.script}.py": SCRIPT_PY.format(
            sample_conf_text=after
        ),
        f"{ConfigGen.directory}/__init__.py": "",
        f"{ConfigGen.directory}/BUILD": "python_sources()",
    }

    rule_runner.write_files(files)


def test_changed(rule_runner: RuleRunner) -> None:
    write_files(
        sample_conf_dir="my_dir",
        sample_conf_file="dummy.conf",
        before="BEFORE",
        after="AFTER",
        rule_runner=rule_runner,
    )

    tgt = rule_runner.get_target(
        Address("my_dir", target_name="t", relative_file_path="dummy.conf")
    )
    fmt_result = run_st2_generate_sample_conf(rule_runner, [tgt])
    assert fmt_result.output == get_snapshot(
        rule_runner, {"my_dir/dummy.conf": "AFTER\n"}
    )
    assert fmt_result.did_change is True


def test_unchanged(rule_runner: RuleRunner) -> None:
    write_files(
        sample_conf_dir="my_dir",
        sample_conf_file="dummy.conf",
        before="AFTER\n",
        after="AFTER",  # print() adds a newline
        rule_runner=rule_runner,
    )

    tgt = rule_runner.get_target(
        Address("my_dir", target_name="t", relative_file_path="dummy.conf")
    )
    fmt_result = run_st2_generate_sample_conf(rule_runner, [tgt])
    assert fmt_result.output == get_snapshot(
        rule_runner, {"my_dir/dummy.conf": "AFTER\n"}
    )
    assert fmt_result.did_change is False
