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

from dataclasses import dataclass
from textwrap import dedent

from pants.backend.python.goals.pytest_runner import (
    PytestPluginSetupRequest,
    PytestPluginSetup,
)
from pants.backend.python.target_types import Executable
from pants.backend.python.util_rules.pex import (
    PexRequest,
    VenvPex,
    VenvPexProcess,
    rules as pex_rules,
)
from pants.engine.fs import CreateDigest, Digest, FileContent
from pants.engine.rules import collect_rules, Get, rule
from pants.engine.process import FallibleProcessResult, ProcessCacheScope
from pants.engine.target import Target
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel

from uses_services.exceptions import ServiceMissingError
from uses_services.platform_rules import Platform
from uses_services.scripts.is_st2cluster_running import (
    __file__ as is_st2cluster_running_full_path,
)
from uses_services.target_types import UsesServicesField


@dataclass(frozen=True)
class UsesSt2ClusterRequest:
    """One or more targets need a running st2 cluster with all st2* services."""

    auth_host: str = "127.0.0.1"
    auth_port: int = 9100
    api_host: str = "127.0.0.1"
    api_port: int = 9101
    stream_host: str = "127.0.0.1"
    stream_port: int = 9102

    @property
    def endpoints(self) -> tuple[tuple[str, str], ...]:
        return (
            (self.auth_host, str(self.auth_port)),
            (self.api_host, str(self.api_port)),
            (self.stream_host, str(self.stream_port)),
        )

    # @classmethod
    # def from_env(cls, env: EnvironmentVars) -> UsesSt2ClusterRequest:
    #    return cls()
    # TODO: consider adding a from_env method using one or both of client => server vars:
    #   ST2_CONFIG_FILE => ST2_CONFIG_PATH (used by many tests, so not safe) or
    #                      ST2_CONF (only in launchdev.sh and st2ctl)
    #   ST2_BASE_URL    => ST2_WEBUI__WEBUI_BASE_URL
    #   ST2_API_URL     => ST2_AUTH__API_URL or
    #                      http{'s' if ST2_API__USE_SSL else ''}://{ST2_API__HOST}:{ST2_API__PORT}
    #   ST2_AUTH_URL    => http://{ST2_AUTH__HOST}:{ST2_AUTH__PORT}
    #   ST2_STREAM_URL  => http://{ST2_STREAM__HOST}:{ST2_STREAM__PORT}
    #   ST2_CACERT (might be needed if using a self-signed cert) => n/a
    # These st2client env vars are irrelevant for the connectivity check:
    #   ST2_AUTH_TOKEN or ST2_API_KEY
    #   ST2_API_VERSION (always "v1" since we don't have anything else)


@dataclass(frozen=True)
class St2ClusterIsRunning:
    pass


class PytestUsesSt2ClusterRequest(PytestPluginSetupRequest):
    @classmethod
    def is_applicable(cls, target: Target) -> bool:
        if not target.has_field(UsesServicesField):
            return False
        uses = target.get(UsesServicesField).value
        return uses is not None and "st2cluster" in uses


@rule(
    desc="Ensure ST2 Cluster is running and accessible before running tests.",
    level=LogLevel.DEBUG,
)
async def st2cluster_is_running_for_pytest(
    request: PytestUsesSt2ClusterRequest,
) -> PytestPluginSetup:
    # this will raise an error if st2cluster is not running
    _ = await Get(St2ClusterIsRunning, UsesSt2ClusterRequest())

    return PytestPluginSetup()


@rule(
    desc="Test to see if ST2 Cluster is running and accessible.",
    level=LogLevel.DEBUG,
)
async def st2cluster_is_running(
    request: UsesSt2ClusterRequest, platform: Platform
) -> St2ClusterIsRunning:
    script_path = "./is_st2cluster_running.py"

    # pants is already watching this directory as it is under a source root.
    # So, we don't need to double watch with PathGlobs, just open it.
    with open(is_st2cluster_running_full_path, "rb") as script_file:
        script_contents = script_file.read()

    script_digest = await Get(
        Digest, CreateDigest([FileContent(script_path, script_contents)])
    )
    script_pex = await Get(
        VenvPex,
        PexRequest(
            output_filename="script.pex",
            internal_only=True,
            sources=script_digest,
            main=Executable(script_path),
        ),
    )

    result = await Get(
        FallibleProcessResult,
        VenvPexProcess(
            script_pex,
            argv=[
                host_or_port
                for endpoint in request.endpoints
                for host_or_port in endpoint
            ],
            input_digest=script_digest,
            description="Checking to see if ST2 Cluster is up and accessible.",
            # this can change from run to run, so don't cache results.
            cache_scope=ProcessCacheScope.PER_SESSION,
            level=LogLevel.DEBUG,
        ),
    )
    is_running = result.exit_code == 0

    if is_running:
        return St2ClusterIsRunning()

    # st2cluster is not running, so raise an error with instructions.
    instructions = dedent(
        """\
        A full StackStorm cluster is required to run some integration tests.
        To start the dev StackStorm cluster, run this from the repo root
        (probably in a new terminal/window, as the output is quite verbose):

        tools/launchdev.sh start -x

        This runs each StackStorm microservice in a tmux session. You can
        inspect the logs for this service in the `logs/` directory.

        If tmux is not installed, please install it with a package manager,
        or use vagrant for local development with something like:

        vagrant init stackstorm/st2
        vagrant up
        vagrant ssh

        Please see: https://docs.stackstorm.com/install/vagrant.html
        """
    )
    raise ServiceMissingError(
        service="st2cluster",
        platform=platform,
        instructions=instructions,
        msg=f"The dev StackStorm cluster seems to be down.\n{instructions}",
    )


def rules():
    return [
        *collect_rules(),
        UnionRule(PytestPluginSetupRequest, PytestUsesSt2ClusterRequest),
        *pex_rules(),
    ]
