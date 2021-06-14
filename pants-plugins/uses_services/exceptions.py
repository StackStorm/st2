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
from uses_services.platform_ import Platform


class ServiceMissingError(Exception):
    """Error raised when a test uses a service but that service is missing."""

    # TODO add special platform handling to DRY instructions across services

    def __init__(self, service, platform: Platform, instructions="", msg=None):
        if msg is None:
            msg = f"The {service} service does not seem to be running or is not accessible!"
            if instructions:
                msg += f"\n{instructions}"
        super().__init__(msg)
        self.service = service
        self.platform = platform
        self.instructions = instructions
