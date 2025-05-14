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
from __future__ import annotations

import os

import pytest

from pants.engine.internals.scheduler import ExecutionError
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .data_fixtures import platform, platform_samples
from .exceptions import ServiceMissingError
from .system_user_rules import (
    HasSystemUser,
    UsesSystemUserRequest,
    rules as system_user_rules,
)
from .platform_rules import Platform


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *system_user_rules(),
            QueryRule(HasSystemUser, (UsesSystemUserRequest, Platform)),
        ],
        target_types=[],
    )


def run_has_system_user(
    rule_runner: RuleRunner,
    uses_system_user_request: UsesSystemUserRequest,
    mock_platform: Platform,
    *,
    extra_args: list[str] | None = None,
) -> HasSystemUser:
    rule_runner.set_options(
        [
            "--backend-packages=uses_services",
            *(extra_args or ()),
        ],
        env_inherit={"PATH", "PYENV_ROOT", "HOME", "ST2TESTS_SYSTEM_USER"},
    )
    result = rule_runner.request(
        HasSystemUser,
        [uses_system_user_request, mock_platform],
    )
    return result


# Warning this requires that system_user is present
def test_system_user_is_present(rule_runner: RuleRunner) -> None:
    request = UsesSystemUserRequest(
        system_user=os.environ.get("ST2TESTS_SYSTEM_USER", "stanley")
    )
    mock_platform = platform(os="TestMock")

    # we are asserting that this does not raise an exception
    has_user = run_has_system_user(rule_runner, request, mock_platform)
    assert has_user


@pytest.mark.parametrize("mock_platform", platform_samples)
def test_system_user_is_absent(
    rule_runner: RuleRunner, mock_platform: Platform
) -> None:
    request = UsesSystemUserRequest(
        system_user="bogus-stanley",
    )

    with pytest.raises(ExecutionError) as exception_info:
        run_has_system_user(rule_runner, request, mock_platform)

    execution_error = exception_info.value
    assert len(execution_error.wrapped_exceptions) == 1

    exc = execution_error.wrapped_exceptions[0]
    assert isinstance(exc, ServiceMissingError)

    assert exc.service == "system_user"
    assert "The system_user (bogus-stanley) does not seem to be present" in str(exc)
    assert not exc.instructions
