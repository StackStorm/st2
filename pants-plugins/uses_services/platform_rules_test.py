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

import dataclasses

import pytest

from pants.testutil.rule_runner import QueryRule, RuleRunner

from .platform_rules import Platform, rules as platform_rules


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *platform_rules(),
            QueryRule(Platform, ()),
        ],
        target_types=[],
    )


def test_get_platform(rule_runner: RuleRunner) -> None:
    rule_runner.set_options(
        ["--backend-packages=uses_services"],
        env_inherit={"PATH", "PYENV_ROOT", "HOME"},
    )

    platform = rule_runner.request(Platform, ())

    assert isinstance(platform, Platform)
    assert dataclasses.is_dataclass(platform)
    # there isn't a good way to inject mocks into the script that
    # the rule_runner runs in a venv. So, there isn't a nice way
    # to test the values of the Platform fields as people could
    # run tests on any platform.
