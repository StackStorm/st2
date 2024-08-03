# Copyright 2024 The StackStorm Authors.
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

import pytest

from pants.testutil.rule_runner import RuleRunner

from pack_metadata.python_rules.python_pack_content import (
    PackContentResourceTargetsOfType,
    PackContentResourceTargetsOfTypeRequest,
)
from pack_metadata.target_types import PackContentResourceTypes


@pytest.mark.parametrize(
    "requested_types,expected_count,expected_file_name",
    (
        # one content type
        ((PackContentResourceTypes.pack_metadata,), 4, "pack.yaml"),
        ((PackContentResourceTypes.pack_config_schema,), 4, "config.schema.yaml"),
        ((PackContentResourceTypes.pack_config_example,), 4, "config.yaml.example"),
        ((PackContentResourceTypes.pack_icon,), 4, "icon.png"),
        ((PackContentResourceTypes.action_metadata,), 5, ".yaml"),
        ((PackContentResourceTypes.sensor_metadata,), 1, ".yaml"),
        ((PackContentResourceTypes.rule_metadata,), 0, ""),
        ((PackContentResourceTypes.policy_metadata,), 0, ""),
        ((PackContentResourceTypes.unknown,), 0, ""),
        # all content types
        ((), 22, ""),
        # some content types
        (
            (
                PackContentResourceTypes.action_metadata,
                PackContentResourceTypes.sensor_metadata,
            ),
            6,
            "",
        ),
        (
            (
                PackContentResourceTypes.pack_metadata,
                PackContentResourceTypes.pack_config_schema,
                PackContentResourceTypes.pack_config_example,
            ),
            12,
            "",
        ),
    ),
)
def test_find_pack_metadata_targets_of_types(
    rule_runner: RuleRunner,
    requested_types: tuple[PackContentResourceTypes, ...],
    expected_count: int,
    expected_file_name: str,
) -> None:
    result = rule_runner.request(
        PackContentResourceTargetsOfType,
        (PackContentResourceTargetsOfTypeRequest(requested_types),),
    )
    assert len(result) == expected_count
    if expected_file_name:
        for tgt in result:
            tgt.address.relative_file_path.endswith(expected_file_name)


def test_find_pack_content_python_entry_points(rule_runner: RuleRunner) -> None:
    pass


def test_find_python_in_pack_lib_directories(rule_runner: RuleRunner) -> None:
    pass
