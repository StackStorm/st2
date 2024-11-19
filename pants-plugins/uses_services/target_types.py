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
from pants.engine.target import StringSequenceField


supported_services = ("mongo", "rabbitmq", "redis", "st2cluster", "system_user")


class UsesServicesField(StringSequenceField):
    alias = "uses"
    help = "Define the services that a test target depends on (mongo, rabbitmq, redis)."
    valid_choices = supported_services
