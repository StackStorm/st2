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

from pants.core.goals.tailor import (
    AllOwnedSources,
    PutativeTarget,
    PutativeTargets,
)
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .tailor import (
    PutativePackMetadataTargetsRequest,
    rules as pack_metadata_rules,
)
from .target_types import PackMetadata, PackMetadataInGitSubmodule


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *pack_metadata_rules(),
            QueryRule(
                PutativeTargets, (PutativePackMetadataTargetsRequest, AllOwnedSources)
            ),
        ],
        target_types=[PackMetadata, PackMetadataInGitSubmodule],
    )


def test_find_putative_targets(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "packs/already_owned/pack.yaml": "---\nname: already_owned\n",
            "packs/already_owned/actions/action.yaml": "---\nname: action\n",
            "packs/foo/pack.yaml": "---\nname: foo\n",
            "packs/foo/actions/action.yaml": "---\nname: action\n",
            "packs/bar/pack.yaml": "---\nname: bar\n",
            "packs/bar/sensors/sensor.yaml": "---\nname: sensor\n",
            "other/deep/baz/pack.yaml": "---\nname: baz\n",
        }
    )
    pts = rule_runner.request(
        PutativeTargets,
        [
            PutativePackMetadataTargetsRequest(
                (
                    "packs",
                    "packs/already_owned",
                    "packs/already_owned/actions",
                    "packs/foo",
                    "packs/foo/actions",
                    "packs/bar",
                    "packs/bar/sensors",
                    "other/deep/baz",
                )
            ),
            AllOwnedSources(
                [
                    "packs/already_owned/pack.yaml",
                    "packs/already_owned/actions/action.yaml",
                ]
            ),
        ],
    )
    assert (
        PutativeTargets(
            [
                PutativeTarget.for_target_type(
                    PackMetadata,
                    path="packs/foo",
                    name="metadata",
                    triggering_sources=["pack.yaml"],
                    kwargs={"name": "metadata"},
                ),
                PutativeTarget.for_target_type(
                    PackMetadata,
                    path="packs/bar",
                    name="metadata",
                    triggering_sources=["pack.yaml"],
                    kwargs={"name": "metadata"},
                ),
                PutativeTarget.for_target_type(
                    PackMetadata,
                    path="other/deep/baz",
                    name="metadata",
                    triggering_sources=["pack.yaml"],
                    kwargs={"name": "metadata"},
                ),
            ]
        )
        == pts
    )
