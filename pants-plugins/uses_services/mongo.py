from dataclasses import dataclass

from textwrap import dedent

# TODO: this is planned / does not exist yet
from pants.backend.python.goals.pytest_runner import (
    PytestPluginSetupRequest,
    PytestPluginSetup,
)
from pants.engine.rules import collect_rules, rule, _uncacheable_rule
from pants.engine.target import Target

from .exceptions import ServiceMissingError
from .platform import Platform


class UsesMongoRequest(PytestPluginSetupRequest):
    @classmethod
    def is_applicable(cls, target: Target) -> bool:
        return "mongo" in target.get(UsesServicesField).value


@dataclass(frozen=True)
class MongoStatus:
    is_running: bool


@_uncacheable_rule
async def mongo_is_running() -> MongoStatus:
    # These config opts are used via oslo_config.cfg.CONF.database.{host,port,db_name}
    # These config opts currently hard-coded in:
    #   for unit tests: st2tests/st2tests/config.py
    #   for integration tests: conf/st2.tests*.conf st2tests/st2tests/fixtures/conf/st2.tests*.conf
    #       (changed by setting ST2_CONFIG_PATH env var inside the tests)
    # TODO: for unit tests: modify code to pull from an env var and then use per-pantsd-slot db_name
    # TODO: for int tests: modify st2.tests*.conf on the fly to set the per-pantsd-slot db_name
    _db_host = "127.0.0.1"  # localhost in test_db.DbConnectionTestCase
    _db_port = 27017
    _db_name = "st2-test"  # st2 in test_db.DbConnectionTestCase

    # so st2-test database gets dropped between:
    #   - each component (st2*/ && various config/ dirs) in Makefile
    #   - DbTestCase/CleanDbTestCase setUpClass

    #   with our version of oslo.config (newer are slower) we can't directly override opts w/ environment variables.

    # Makefile
    #    .run-unit-tests-with-coverage (<- .combine-unit-tests-coverage <- .coverage.unit <- .unit-tests-coverage-html <- ci-unit <- ci)
    #        echo "----- Dropping st2-test db -----"
    #        mongo st2-test --eval "db.dropDatabase();"
    #        for component in $(COMPONENTS_TEST)
    #            nosetests $(NOSE_OPTS) -s -v $(NOSE_COVERAGE_FLAGS) $(NOSE_COVERAGE_PACKAGES) $$component/tests/unit

    # TODO: logic to determine if it is running
    # maybe something like https://stackoverflow.com/a/53640204
    # https://github.com/Lucas-C/dotfiles_and_notes/blob/master/languages/python/mongo_ping_client.py
    # download it?
    return MongoStatus(True)


@rule
async def assert_mongo_is_running(
    request: UsesMongoRequest, mongo_status: MongoStatus, platform: Platform
) -> PytestPluginSetup:
    if not mongo_status.is_running:
        elif platform.distro in ["centos", "rhel"] or "rhel" in platform.like:
            insturctions = dedent(
                f"""\
                If mongo is installed, but not running try:

                """
            )

            if platform.major_version == "7"
                instructions += "\nservice mongo start\n"
            else:
                instructions += "\nsystemctl start mongod\n"

            instructions += dedent(
                """
                If mongo is not installed, this is one way to install it:

                # Add key and repo for the latest stable MongoDB (4.0)
                rpm --import https://www.mongodb.org/static/pgp/server-4.0.asc
                sh -c "cat <<EOT > /etc/yum.repos.d/mongodb-org-4.repo
                [mongodb-org-4]
                name=MongoDB Repository
                baseurl=https://repo.mongodb.org/yum/redhat/${OSRELEASE_VERSION}/mongodb-org/4.0/x86_64/
                gpgcheck=1
                enabled=1
                gpgkey=https://www.mongodb.org/static/pgp/server-4.0.asc
                EOT"
                # install mongo
                yum install mongodb-org
                # Don't forget to start mongo.
                """
            )
        elif platform.distro in ["ubuntu", "debian"] or "debian" in distro.like:
            insturctions = dedent(
                """\
                If mongo is installed, but not running try:

                systemctl start mongod

                If mongo is not installed, this is one way to install it:

                apt-get install mongodb mongodb-server
                # Don't forget to start mongo.
                """
            )
        elif platform.os == "Linux":
            insturctions = dedent(
                f"""\
                You are on Linux using {platform.distro_name}, which is not
                one of our generally supported distributions. We recommend
                you use vagrant for local development with something like:

                vagrant init stackstorm/st2
                vagrant up
                vagrant ssh

                Please see: https://docs.stackstorm.com/install/vagrant.html

                For anyone who wants to attempt local development without vagrant,
                you are pretty much on your own. At a minimum you need to install
                and start mongo with something like:

                systemctl start mongod

                We would be interested to hear about alternative distros people
                are using for development. If you are able, please let us know
                on slack which distro you are using:

                Arch: {platform.arch}
                Distro: {platform.distro}
                Distro Codename: {platform.distro_codename}
                Distro Version: {platform.distro_version}

                Thanks and Good Luck!
                """
            )
        elif platform.os == "Darwin":  # MacOS
            insturctions = dedent(
                """\
                You are on Mac OS. Generally we recommend using vagrant for local
                development on Mac OS with something like:

                vagrant init stackstorm/st2
                vagrant up
                vagrant ssh

                Please see: https://docs.stackstorm.com/install/vagrant.html

                For anyone who wants to attempt local development without vagrant,
                you may run into some speed bumps. Others StackStorm developers have
                been known to use Mac OS for development, so feel free to ask for
                help in slack. At a minimum you need to install and start mongo.
                """
            )
        else:
            insturctions = dedent(
                """\
                You are not on Linux. In this case we recommend using vagrant
                for local development with something like:

                vagrant init stackstorm/st2
                vagrant up
                vagrant ssh

                Please see: https://docs.stackstorm.com/install/vagrant.html

                For anyone who wants to attempt local development without vagrant,
                you are pretty much on your own. At a minimum you need to install
                and start mongo. Good luck!
                """
            )

        raise ServiceMissingError("mongo", platform, instructions)

    return PytestPluginSetup()


def rules():
    return collect_rules()
