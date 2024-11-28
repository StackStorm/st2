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

import socket

from contextlib import closing

import pytest

from pants.engine.internals.scheduler import ExecutionError
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .data_fixtures import platform, platform_samples
from .exceptions import ServiceMissingError
from .st2cluster_rules import (
    St2ClusterIsRunning,
    UsesSt2ClusterRequest,
    rules as st2cluster_rules,
)
from .platform_rules import Platform


@pytest.fixture
def rule_runner() -> RuleRunner:
    return RuleRunner(
        rules=[
            *st2cluster_rules(),
            QueryRule(St2ClusterIsRunning, (UsesSt2ClusterRequest, Platform)),
        ],
        target_types=[],
    )


def run_st2cluster_is_running(
    rule_runner: RuleRunner,
    uses_st2cluster_request: UsesSt2ClusterRequest,
    mock_platform: Platform,
    *,
    extra_args: list[str] | None = None,
) -> St2ClusterIsRunning:
    rule_runner.set_options(
        [
            "--backend-packages=uses_services",
            *(extra_args or ()),
        ],
        env_inherit={"PATH", "PYENV_ROOT", "HOME"},
    )
    result = rule_runner.request(
        St2ClusterIsRunning,
        [uses_st2cluster_request, mock_platform],
    )
    return result


@pytest.fixture
def mock_st2cluster() -> tuple[int, int, int]:
    sock1: socket.socket
    sock2: socket.socket
    sock3: socket.socket
    with (
        closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock1,
        closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock2,
        closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock3,
    ):
        socks = (sock1, sock2, sock3)
        for sock in socks:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
        ports = tuple(sock.getsockname()[1] for sock in socks)
        yield ports


# Warning this requires that st2cluster be running
def test_st2cluster_is_running(
    rule_runner: RuleRunner, mock_st2cluster: tuple[int, int, int]
) -> None:
    request = UsesSt2ClusterRequest(
        auth_port=mock_st2cluster[0],
        api_port=mock_st2cluster[1],
        stream_port=mock_st2cluster[2],
    )
    mock_platform = platform(os="TestMock")

    # we are asserting that this does not raise an exception
    is_running = run_st2cluster_is_running(rule_runner, request, mock_platform)
    assert is_running


@pytest.mark.parametrize("mock_platform", platform_samples)
def test_st2cluster_not_running(
    rule_runner: RuleRunner, mock_platform: Platform
) -> None:
    request = UsesSt2ClusterRequest(
        # some unassigned ports that are unlikely to be used
        auth_port=10,
        api_port=12,
        stream_port=14,
    )

    with pytest.raises(ExecutionError) as exception_info:
        run_st2cluster_is_running(rule_runner, request, mock_platform)

    execution_error = exception_info.value
    assert len(execution_error.wrapped_exceptions) == 1

    exc = execution_error.wrapped_exceptions[0]
    assert isinstance(exc, ServiceMissingError)

    assert exc.service == "st2cluster"
    assert "The dev StackStorm cluster seems to be down" in str(exc)
    assert exc.instructions != ""
