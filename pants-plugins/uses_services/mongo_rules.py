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
import os

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
from pants.engine.fs import CreateDigest, Digest, FileContent
from pants.engine.rules import collect_rules, Get, MultiGet, rule
from pants.engine.process import FallibleProcessResult, ProcessCacheScope
from pants.engine.target import Target
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel

from uses_services.exceptions import ServiceMissingError, ServiceSpecificMessages
from uses_services.platform_rules import Platform
from uses_services.scripts.is_mongo_running import (
    __file__ as is_mongo_running_full_path,
)
from uses_services.target_types import UsesServicesField


@dataclass(frozen=True)
class UsesMongoRequest:
    """One or more targets need a running mongo service using these settings.

    The db_* attributes represent the db connection settings from st2.conf.
    In st2 code, they come from:
        oslo_config.cfg.CONF.database.{host,port,db_name,connection_timeout}
    """

    # These config opts currently hard-coded in:
    #   for unit tests: st2tests/st2tests/config.py
    #   for integration tests: conf/st2.tests*.conf st2tests/st2tests/fixtures/conf/st2.tests*.conf
    #       (changed by setting ST2_CONFIG_PATH env var inside the tests)
    # TODO: for unit tests: modify code to pull db connect settings from env vars
    # TODO: for int tests: modify st2.tests*.conf on the fly to set the per-pantsd-slot db_name
    #                      and either add env vars for db connect settings or modify conf files as well

    #   with our version of oslo.config (newer are slower) we can't directly override opts w/ environment variables.

    db_host: str = "127.0.0.1"  # localhost in test_db.DbConnectionTestCase
    db_port: int = 27017
    # db_name is "st2" in test_db.DbConnectionTestCase
    db_name: str = f"st2-test{os.environ.get('ST2TESTS_PARALLEL_SLOT', '')}"
    db_connection_timeout: int = 3000


@dataclass(frozen=True)
class MongoIsRunning:
    pass


class PytestUsesMongoRequest(PytestPluginSetupRequest):
    @classmethod
    def is_applicable(cls, target: Target) -> bool:
        if not target.has_field(UsesServicesField):
            return False
        uses = target.get(UsesServicesField).value
        return uses is not None and "mongo" in uses


@rule(
    desc="Ensure mongodb is running and accessible before running tests.",
    level=LogLevel.DEBUG,
)
async def mongo_is_running_for_pytest(
    request: PytestUsesMongoRequest,
) -> PytestPluginSetup:
    # TODO: delete these comments once the Makefile becomes irrelevant.
    #       the comments explore how the Makefile prepares to run and runs tests

    # The st2-test database gets dropped between (in Makefile based testing):
    #   - each component (st2*/ && various config/ dirs) in Makefile
    #   - DbTestCase/CleanDbTestCase setUpClass

    # Makefile
    #    .run-unit-tests-coverage (<- .combine-unit-tests-coverage <- .coverage.unit <- .unit-tests-coverage-html <- ci-unit <- ci)
    #        echo "----- Dropping st2-test db -----"
    #        mongo st2-test --eval "db.dropDatabase();"
    #        for component in $(COMPONENTS_TEST)
    #            nosetests $(NOSE_OPTS) -s -v $(NOSE_COVERAGE_FLAGS) $(NOSE_COVERAGE_PACKAGES) $$component/tests/unit

    # this will raise an error if mongo is not running
    _ = await Get(MongoIsRunning, UsesMongoRequest())

    return PytestPluginSetup()


@rule(
    desc="Test to see if mongodb is running and accessible.",
    level=LogLevel.DEBUG,
)
async def mongo_is_running(
    request: UsesMongoRequest, platform: Platform
) -> MongoIsRunning:
    script_path = "./is_mongo_running.py"

    # pants is already watching this directory as it is under a source root.
    # So, we don't need to double watch with PathGlobs, just open it.
    with open(is_mongo_running_full_path, "rb") as script_file:
        script_contents = script_file.read()

    script_digest, mongoengine_pex = await MultiGet(
        Get(Digest, CreateDigest([FileContent(script_path, script_contents)])),
        Get(
            VenvPex,
            PexRequest(
                output_filename="mongoengine.pex",
                internal_only=True,
                requirements=PexRequirements({"mongoengine", "pymongo"}),
            ),
        ),
    )

    result = await Get(
        FallibleProcessResult,
        VenvPexProcess(
            mongoengine_pex,
            argv=(
                script_path,
                request.db_host,
                str(request.db_port),
                request.db_name,
                str(request.db_connection_timeout),
            ),
            input_digest=script_digest,
            description="Checking to see if Mongo is up and accessible.",
            # this can change from run to run, so don't cache results.
            cache_scope=ProcessCacheScope.PER_SESSION,
            level=LogLevel.DEBUG,
        ),
    )
    is_running = result.exit_code == 0

    if is_running:
        return MongoIsRunning()

    # mongo is not running, so raise an error with instructions.
    raise ServiceMissingError.generate(
        platform=platform,
        messages=ServiceSpecificMessages(
            service="mongo",
            service_start_cmd_el_7="service mongo start",
            service_start_cmd_el="systemctl start mongod",
            not_installed_clause_el="this is one way to install it:",
            install_instructions_el=dedent(
                """\
                # Add key and repo for the latest stable MongoDB (4.0)
                sudo rpm --import https://www.mongodb.org/static/pgp/server-4.0.asc
                sudo sh -c "cat <<EOT > /etc/yum.repos.d/mongodb-org-4.repo
                [mongodb-org-4]
                name=MongoDB Repository
                baseurl=https://repo.mongodb.org/yum/redhat/${OSRELEASE_VERSION}/mongodb-org/4.0/x86_64/
                gpgcheck=1
                enabled=1
                gpgkey=https://www.mongodb.org/static/pgp/server-4.0.asc
                EOT"
                # Install mongo
                sudo yum -y install mongodb-org
                # Don't forget to start mongo.
                """
            ),
            service_start_cmd_deb="systemctl start mongod",
            not_installed_clause_deb="this is one way to install it:",
            install_instructions_deb=dedent(
                """\
                sudo apt-get install -y mongodb-org
                # Don't forget to start mongo.
                """
            ),
            service_start_cmd_generic="systemctl start mongod",
        ),
    )


def rules():
    return [
        *collect_rules(),
        UnionRule(PytestPluginSetupRequest, PytestUsesMongoRequest),
        *pex_rules(),
    ]
