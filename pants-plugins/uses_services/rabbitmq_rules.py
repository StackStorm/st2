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
from typing import Tuple

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
from uses_services.scripts.is_rabbitmq_running import (
    __file__ as is_rabbitmq_running_full_path,
)
from uses_services.target_types import UsesServicesField


@dataclass(frozen=True)
class UsesRabbitMQRequest:
    """One or more targets need a running rabbitmq service using these settings.

    The mq_* attributes represent the messaging settings from st2.conf.
    In st2 code, they come from:
        oslo_config.cfg.CONF.messaging.{url,cluster_urls}
    """

    # These config opts for integration tests are in:
    #   conf/st2.tests*.conf st2tests/st2tests/fixtures/conf/st2.tests*.conf
    #       (changed by setting ST2_CONFIG_PATH env var inside the tests)
    # These can also be updated via the ST2_MESSAGING_* env vars (which oslo_config reads).
    # Integration tests should pass these changes onto subprocesses via the same env vars.

    mq_urls: Tuple[str] = ("amqp://guest:guest@127.0.0.1:5672//",)

    @classmethod
    def from_env(cls, env: EnvironmentVars) -> UsesRabbitMQRequest:
        default = cls()
        url = env.get("ST2_MESSAGING__URL", None)
        mq_urls = (url,) if url else default.mq_urls
        return UsesRabbitMQRequest(mq_urls=mq_urls)


@dataclass(frozen=True)
class RabbitMQIsRunning:
    pass


class PytestUsesRabbitMQRequest(PytestPluginSetupRequest):
    @classmethod
    def is_applicable(cls, target: Target) -> bool:
        if not target.has_field(UsesServicesField):
            return False
        uses = target.get(UsesServicesField).value
        return uses is not None and "rabbitmq" in uses


@rule(
    desc="Ensure rabbitmq is running and accessible before running tests.",
    level=LogLevel.DEBUG,
)
async def rabbitmq_is_running_for_pytest(
    request: PytestUsesRabbitMQRequest,
    test_extra_env: TestExtraEnv,
) -> PytestPluginSetup:
    # this will raise an error if rabbitmq is not running
    _ = await Get(
        RabbitMQIsRunning, UsesRabbitMQRequest.from_env(env=test_extra_env.env)
    )

    return PytestPluginSetup()


@rule(
    desc="Test to see if rabbitmq is running and accessible.",
    level=LogLevel.DEBUG,
)
async def rabbitmq_is_running(
    request: UsesRabbitMQRequest, platform: Platform
) -> RabbitMQIsRunning:
    script_path = "./is_rabbitmq_running.py"

    # pants is already watching this directory as it is under a source root.
    # So, we don't need to double watch with PathGlobs, just open it.
    with open(is_rabbitmq_running_full_path, "rb") as script_file:
        script_contents = script_file.read()

    script_digest, kombu_pex = await MultiGet(
        Get(Digest, CreateDigest([FileContent(script_path, script_contents)])),
        Get(
            VenvPex,
            PexRequest(
                output_filename="kombu.pex",
                internal_only=True,
                requirements=PexRequirements({"kombu"}),
            ),
        ),
    )

    result = await Get(
        FallibleProcessResult,
        VenvPexProcess(
            kombu_pex,
            argv=(
                script_path,
                *request.mq_urls,
            ),
            input_digest=script_digest,
            description="Checking to see if RabbitMQ is up and accessible.",
            # this can change from run to run, so don't cache results.
            cache_scope=ProcessCacheScope.PER_SESSION,
            level=LogLevel.DEBUG,
        ),
    )
    is_running = result.exit_code == 0

    if is_running:
        return RabbitMQIsRunning()

    # rabbitmq is not running, so raise an error with instructions.
    raise ServiceMissingError.generate(
        platform=platform,
        messages=ServiceSpecificMessages(
            service="rabbitmq",
            service_start_cmd_el_7="service rabbitmq-server start",
            service_start_cmd_el="systemctl start rabbitmq-server",
            not_installed_clause_el="this is one way to install it:",
            install_instructions_el=dedent(
                """\
                # Add key and repo for erlang and RabbitMQ
                curl -sL https://packagecloud.io/install/repositories/rabbitmq/erlang/script.rpm.sh | sudo bash
                curl -sL https://packagecloud.io/install/repositories/rabbitmq/rabbitmq-server/script.rpm.sh | sudo bash
                sudo yum makecache -y --disablerepo='*' --enablerepo='rabbitmq_rabbitmq-server'
                # Check for any required version constraints in our docs:
                # https://docs.stackstorm.com/latest/install/rhel{platform.distro_major_version}.html

                # Install erlang and RabbitMQ (and possibly constrain the version)
                sudo yum -y install erlang{'' if platform.distro_major_version == "7" else '-*'}
                sudo yum -y install rabbitmq-server
                # Don't forget to start rabbitmq-server.
                """
            ),
            service_start_cmd_deb="systemctl start rabbitmq-server",
            not_installed_clause_deb="try the quick start script here:",
            install_instructions_deb=dedent(
                """\
                https://www.rabbitmq.com/install-debian.html#apt-cloudsmith
                """
            ),
            service_start_cmd_generic="systemctl start rabbitmq-server",
            env_vars_hint=dedent(
                """\
                You can also export the ST2_MESSAGING__URL env var to automatically use any
                RabbitMQ host, local or remote, while running unit and integration tests.
                If needed, you can also override the default exchange/queue name prefix
                by exporting ST2_MESSAGING__PREFIX. Note that tests always add a numeric
                suffix to the exchange/queue name prefix so that tests can safely run
                in parallel.
                """
            ),
        ),
    )


def rules():
    return [
        *collect_rules(),
        UnionRule(PytestPluginSetupRequest, PytestUsesRabbitMQRequest),
        *pex_rules(),
    ]
