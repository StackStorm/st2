from enum import Enum
from typing import Iterable, Optional, Tuple

from pants.backend.python.target_types import PythonTests
from pants.engine.addresses import Address
from pants.engine.target import (
    InvalidFieldChoiceException,
    StringSequenceField,
    StringField,
)

# from . import mongo
from . import platform


supported_services = ("mongo", "rabbitmq", "redis")


class UsesServicesField(StringSequenceField):
    alias = "uses"
    help = "Define the services that a test target depends on (mongo, rabbitmq, redis)."
    valid_choices = supported_services

    @classmethod
    def compute_value(
        cls, raw_value: Optional[Iterable[str]], address: Address
    ) -> Optional[Tuple[str, ...]]:
        services = super().compute_value(raw_value, address)
        if not services:
            return services
        for service in services:
            if service not in cls.valid_choices:
                raise InvalidFieldChoiceException(
                    address, cls.alias, service, valid_choices=valid_choices
                )


def rules():
    return [
        PythonTests.register_plugin_field(UsesServicesField),
        *platform.rules(),
        # *mongo.rules(),
    ]


# def target_types():
#     return [CustomTargetType]
