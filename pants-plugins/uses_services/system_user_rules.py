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
from pants.core.goals.test import TestExtraEnv
from pants.engine.fs import CreateDigest, Digest, FileContent
from pants.engine.rules import collect_rules, Get, rule
from pants.engine.process import FallibleProcessResult, ProcessCacheScope
from pants.engine.target import Target
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel

from uses_services.exceptions import ServiceMissingError
from uses_services.platform_rules import Platform
from uses_services.scripts.has_system_user import (
    __file__ as has_system_user_full_path,
)
from uses_services.target_types import UsesServicesField


@dataclass(frozen=True)
class UsesSystemUserRequest:
    """One or more targets need the system_user (like stanley) using these settings.

    The system_user attributes represent the system_user.user settings from st2.conf.
    In st2 code, they come from:
        oslo_config.cfg.CONF.system_user.user
    """

    system_user: str = "stanley"


@dataclass(frozen=True)
class HasSystemUser:
    pass


class PytestUsesSystemUserRequest(PytestPluginSetupRequest):
    @classmethod
    def is_applicable(cls, target: Target) -> bool:
        if not target.has_field(UsesServicesField):
            return False
        uses = target.get(UsesServicesField).value
        return uses is not None and "system_user" in uses


@rule(
    desc="Ensure system_user is present before running tests.",
    level=LogLevel.DEBUG,
)
async def has_system_user_for_pytest(
    request: PytestUsesSystemUserRequest,
    test_extra_env: TestExtraEnv,
) -> PytestPluginSetup:
    system_user = test_extra_env.env.get("ST2TESTS_SYSTEM_USER", "stanley")

    # this will raise an error if system_user is not present
    _ = await Get(HasSystemUser, UsesSystemUserRequest(system_user=system_user))

    return PytestPluginSetup()


@rule(
    desc="Test to see if system_user is present.",
    level=LogLevel.DEBUG,
)
async def has_system_user(
    request: UsesSystemUserRequest, platform: Platform
) -> HasSystemUser:
    script_path = "./has_system_user.py"

    # pants is already watching this directory as it is under a source root.
    # So, we don't need to double watch with PathGlobs, just open it.
    with open(has_system_user_full_path, "rb") as script_file:
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
            argv=(request.system_user,),
            description="Checking to see if system_user is present.",
            # this can change from run to run, so don't cache results.
            cache_scope=ProcessCacheScope.PER_SESSION,
            level=LogLevel.DEBUG,
        ),
    )
    has_user = result.exit_code == 0

    if has_user:
        return HasSystemUser()

    current_user = result.stdout.decode().strip()

    # system_user is not present, so raise an error with instructions.
    raise ServiceMissingError(
        service="system_user",
        platform=platform,
        msg=dedent(
            f"""\
            The system_user ({request.system_user}) does not seem to be present!

            Please export the ST2TESTS_SYSTEM_USER env var to specify which user
            tests should use as the system_user. This user must be present on
            your system.

            To use your current user ({current_user}) as the system_user, run:

            export ST2TESTS_SYSTEM_USER=$(id -un)
            """
        ),
    )


def rules():
    return [
        *collect_rules(),
        UnionRule(PytestPluginSetupRequest, PytestUsesSystemUserRequest),
        *pex_rules(),
    ]
