# coding: utf-8
from typing import Iterable, Optional, Tuple

from pants.build_graph.address import Address
from pants.engine.target import InvalidFieldChoiceException, StringSequenceField


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
                    address, cls.alias, service, valid_choices=cls.valid_choices
                )
        return tuple(services)
