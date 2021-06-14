# Copyright 2021 The StackStorm Authors.
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
