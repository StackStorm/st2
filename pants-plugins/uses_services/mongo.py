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
    # TODO: logic to determine if it is running
    # maybe something like https://stackoverflow.com/a/53640204
    # https://github.com/Lucas-C/dotfiles_and_notes/blob/master/languages/python/mongo_ping_client.py
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
