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

from pants.engine.internals.scheduler import ExecutionError
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .data_fixtures import platform, platform_samples
from .exceptions import ServiceMissingError
from .redis_rules import (
    RedisIsRunning,
    UsesRedisRequest,
    rules as redis_rules,
)
from .platform_rules import Platform


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *redis_rules(),
            QueryRule(RedisIsRunning, (UsesRedisRequest, Platform)),
        ],
        target_types=[],
    )


def run_redis_is_running(
    rule_runner: RuleRunner,
    uses_redis_request: UsesRedisRequest,
    mock_platform: Platform,
    *,
    extra_args: list[str] | None = None,
) -> RedisIsRunning:
    rule_runner.set_options(
        [
            "--backend-packages=uses_services",
            *(extra_args or ()),
        ],
        env_inherit={
            "PATH",
            "PYENV_ROOT",
            "HOME",
            "ST2TESTS_REDIS_HOST",
            "ST2TESTS_REDIS_PORT",
            "ST2TESTS_PARALLEL_SLOT",
        },
    )
    result = rule_runner.request(
        RedisIsRunning,
        [uses_redis_request, mock_platform],
    )
    return result


# Warning this requires that redis be running
def test_redis_is_running(rule_runner: RuleRunner) -> None:
    request = UsesRedisRequest.from_env(env=rule_runner.environment)
    mock_platform = platform(os="TestMock")

    # we are asserting that this does not raise an exception
    is_running = run_redis_is_running(rule_runner, request, mock_platform)
    assert is_running


@pytest.mark.parametrize("mock_platform", platform_samples)
def test_redis_not_running(rule_runner: RuleRunner, mock_platform: Platform) -> None:
    request = UsesRedisRequest(
        host="127.100.20.7",
        port=10,  # 10 is an unassigned port, unlikely to be used
    )

    with pytest.raises(ExecutionError) as exception_info:
        run_redis_is_running(rule_runner, request, mock_platform)

    execution_error = exception_info.value
    assert len(execution_error.wrapped_exceptions) == 1

    exc = execution_error.wrapped_exceptions[0]
    assert isinstance(exc, ServiceMissingError)

    assert exc.service == "redis"
    assert "The redis service does not seem to be running" in str(exc)
    assert exc.instructions != ""
