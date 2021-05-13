# TODO: this is planned / does not exist yet
from pants.backend.python.goals.pytest_runner import (
    PytestPluginSetupRequest,
    PytestPluginSetup,
)
from pants.engine.rules import collect_rules, rule
from pants.engine.target import Target

from .exceptions import ServiceMissingError


class UsesMongoRequest(PytestPluginSetupRequest):
    @classmethod
    def is_applicable(cls, target: Target) -> bool:
        return "mongo" in target.get(UsesServicesField).value


@rule
def assert_mongo_is_running(request: UsesMongoRequest) -> PytestPluginSetup:
    mongo_is_running = True
    # TODO: logic to determine if it is running
    if not mongo_is_running:
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
