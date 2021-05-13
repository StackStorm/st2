from dataclasses import dataclass

# TODO: this is planned / does not exist yet
from pants.backend.python.goals.pytest_runner import (
    PytestPluginSetupRequest,
    PytestPluginSetup,
)
from pants.engine.rules import collect_rules, rule, _uncacheable_rule
from pants.engine.target import Target

from .exceptions import ServiceMissingError


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
def assert_mongo_is_running(request: UsesMongoRequest, mongo_status: MongoStatus) -> PytestPluginSetup:
    if not mongo_status.is_running:
        platform = ""  # TODO: lookup

        if platform == "CentOS7":
            insturctions = """
                helpful instructions for installation / running required service
                """
        elif platform == "CentOS8":
            insturctions = """
                helpful instructions for installation / running required service
                """
        elif platform == "Ubuntu":
            insturctions = """
                helpful instructions for installation / running required service
                """
        elif platform == "MacOSX":
            insturctions = """
                helpful instructions for installation / running required service
                """
        else:
            insturctions = """
                helpful instructions for installation / running required service
                """

        raise ServiceMissingError(instructions)

    return PytestPluginSetup()


def rules():
    return collect_rules()
