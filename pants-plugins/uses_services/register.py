from enum import Enum
from typing import Iterable, Optional, Tuple

# from pants.backend.python.goals.pytest_runner import PytestPluginSetupRequest, PytestPluginSetup
from pants.backend.python.target_types import PythonTests
from pants.engine.addresses import Address
from pants.engine.target import InvalidFieldChoiceException, StringSequenceField, StringField


class Service(Enum):
    MONGO = "mongo"
    RABBITMQ = "rabbitmq"
    REDIS = "redis"


class UsesServices(StringSequenceField):
    alias = "uses"
    help = "Define the services that a test target depends on (mongo, rabbitmq, redis)."
    valid_choices = Service

    @classmethod
    def compute_value(
        cls, raw_value: Optional[Iterable[str]], address: Address
    ) -> Optional[Tuple[str, ...]]:
        services = super().compute_value(raw_value, address)
        if not services:
            return services
        valid_choices = (choice.value for choice in cls.valid_choices)
        for service in services:
            if service not in valid_choices:
                raise InvalidFieldChoiceException(
                    address, cls.alias, service, valid_choices=valid_choices
                )


def rules():
    return [PythonTests.register_plugin_field(UsesServices)]


# def target_types():
#     return [CustomTargetType]
