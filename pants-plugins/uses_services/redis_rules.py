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

from dataclasses import dataclass
from textwrap import dedent

from pants.backend.python.goals.pytest_runner import (
    PytestPluginSetupRequest,
    PytestPluginSetup,
)
from pants.backend.python.util_rules.pex import (
    PexRequest,
    PexRequirements,
    VenvPex,
    VenvPexProcess,
    rules as pex_rules,
)
from pants.core.goals.test import TestExtraEnv
from pants.engine.env_vars import EnvironmentVars
from pants.engine.fs import CreateDigest, Digest, FileContent
from pants.engine.rules import collect_rules, Get, MultiGet, rule
from pants.engine.process import FallibleProcessResult, ProcessCacheScope
from pants.engine.target import Target
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel

from uses_services.exceptions import ServiceMissingError, ServiceSpecificMessages
from uses_services.platform_rules import Platform
from uses_services.scripts.is_redis_running import (
    __file__ as is_redis_running_full_path,
)
from uses_services.target_types import UsesServicesField


@dataclass(frozen=True)
class UsesRedisRequest:
    """One or more targets need a running redis service using these settings.

    The coord_* attributes represent the coordination settings from st2.conf.
    In st2 code, they come from:
        oslo_config.cfg.CONF.coordination.url
    """

    # These config opts for integration tests are in:
    #   conf/st2.dev.conf (copied to conf/st2.ci.conf)
    # These can also be updated via the ST2TESTS_REDIS_* env vars.
    # Integration tests should pass these changes onto subprocesses using the
    # ST2_COORDINATION__* env vars (which oslo_config reads).

    host: str = "127.0.0.1"
    port: int = 6379

    @property
    def coord_url(self) -> str:
        return f"redis://{self.host}:{self.port}?namespace=_st2_test"

    @classmethod
    def from_env(cls, env: EnvironmentVars) -> UsesRedisRequest:
        default = cls()
        host = env.get("ST2TESTS_REDIS_HOST", default.host)
        port_raw = env.get("ST2TESTS_REDIS_PORT", str(default.port))

        try:
            port = int(port_raw)
        except (TypeError, ValueError):
            port = default.port

        return cls(host=host, port=port)


@dataclass(frozen=True)
class RedisIsRunning:
    pass


class PytestUsesRedisRequest(PytestPluginSetupRequest):
    @classmethod
    def is_applicable(cls, target: Target) -> bool:
        if not target.has_field(UsesServicesField):
            return False
        uses = target.get(UsesServicesField).value
        return uses is not None and "redis" in uses


@rule(
    desc="Ensure redis is running and accessible before running tests.",
    level=LogLevel.DEBUG,
)
async def redis_is_running_for_pytest(
    request: PytestUsesRedisRequest,
    test_extra_env: TestExtraEnv,
) -> PytestPluginSetup:
    # this will raise an error if redis is not running
    _ = await Get(RedisIsRunning, UsesRedisRequest.from_env(env=test_extra_env.env))

    return PytestPluginSetup()


@rule(
    desc="Test to see if redis is running and accessible.",
    level=LogLevel.DEBUG,
)
async def redis_is_running(
    request: UsesRedisRequest, platform: Platform
) -> RedisIsRunning:
    script_path = "./is_redis_running.py"

    # pants is already watching this directory as it is under a source root.
    # So, we don't need to double watch with PathGlobs, just open it.
    with open(is_redis_running_full_path, "rb") as script_file:
        script_contents = script_file.read()

    script_digest, tooz_pex = await MultiGet(
        Get(Digest, CreateDigest([FileContent(script_path, script_contents)])),
        Get(
            VenvPex,
            PexRequest(
                output_filename="tooz.pex",
                internal_only=True,
                requirements=PexRequirements({"tooz", "redis"}),
            ),
        ),
    )

    result = await Get(
        FallibleProcessResult,
        VenvPexProcess(
            tooz_pex,
            argv=(
                script_path,
                request.coord_url,
            ),
            input_digest=script_digest,
            description="Checking to see if Redis is up and accessible.",
            # this can change from run to run, so don't cache results.
            cache_scope=ProcessCacheScope.PER_SESSION,
            level=LogLevel.DEBUG,
        ),
    )
    is_running = result.exit_code == 0

    if is_running:
        return RedisIsRunning()

    # redis is not running, so raise an error with instructions.
    raise ServiceMissingError.generate(
        platform=platform,
        messages=ServiceSpecificMessages(
            service="redis",
            service_start_cmd_el_7="service redis start",
            service_start_cmd_el="systemctl start redis",
            not_installed_clause_el="this is one way to install it:",
            install_instructions_el=dedent(
                """\
                sudo yum -y install redis
                # Don't forget to start redis.
                """
            ),
            service_start_cmd_deb="systemctl start redis",
            not_installed_clause_deb="this is one way to install it:",
            install_instructions_deb=dedent(
                """\
                sudo apt-get install -y redis
                # Don't forget to start redis.
                """
            ),
            service_start_cmd_generic="systemctl start redis",
            env_vars_hint=dedent(
                """\
                You can also export the ST2TESTS_REDIS_HOST and ST2TESTS_REDIS_PORT
                env vars to automatically use any redis host, local or remote,
                while running unit and integration tests. Tests do not use any
                ST2_COORDINATION__* vars at this point.
                """
            ),
        ),
    )


def rules():
    return [
        *collect_rules(),
        UnionRule(PytestPluginSetupRequest, PytestUsesRedisRequest),
        *pex_rules(),
    ]
