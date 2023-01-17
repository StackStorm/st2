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

from pants.engine.addresses import Address
from pants.engine.target import SourcesPaths, SourcesPathsRequest
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .target_types import (
    PackMetadata,
    # PackMetadataSourcesField,
    PackMetadataInGitSubmodule,
    PackMetadataInGitSubmoduleSources,
    UnmatchedGlobsError,
)


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            QueryRule(SourcesPaths, [SourcesPathsRequest]),
        ],
        target_types=[PackMetadata, PackMetadataInGitSubmodule],
    )


GIT_SUBMODULE_BUILD_FILE = """
pack_metadata_in_git_submodule(
    name="metadata",
    sources=["./submodule_dir/pack.yaml"],
)
"""


def test_git_submodule_sources_missing(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "packs/BUILD": GIT_SUBMODULE_BUILD_FILE,
        }
    )
    tgt = rule_runner.get_target(Address("packs", target_name="metadata"))

    with pytest.raises(UnmatchedGlobsError):
        _ = rule_runner.request(
            SourcesPaths, [SourcesPathsRequest(tgt[PackMetadataInGitSubmoduleSources])]
        )


def test_git_submodule_sources_present(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "packs/BUILD": GIT_SUBMODULE_BUILD_FILE,
            "packs/submodule_dir/pack.yaml": "---\nname: foobar\n",
        }
    )
    tgt = rule_runner.get_target(Address("packs", target_name="metadata"))

    # basically: this asserts that it does not raise UnmatchedGlobsError
    _ = rule_runner.request(
        SourcesPaths, [SourcesPathsRequest(tgt[PackMetadataInGitSubmoduleSources])]
    )
