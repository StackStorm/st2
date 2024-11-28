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
from pants.backend.python.target_types import (
    PythonTestTarget,
    PythonTestsGeneratorTarget,
)

from uses_services import (
    mongo_rules,
    platform_rules,
    rabbitmq_rules,
    redis_rules,
    st2cluster_rules,
    system_user_rules,
)
from uses_services.target_types import UsesServicesField


def rules():
    return [
        PythonTestsGeneratorTarget.register_plugin_field(
            UsesServicesField, as_moved_field=True
        ),
        PythonTestTarget.register_plugin_field(UsesServicesField),
        *platform_rules.rules(),
        *mongo_rules.rules(),
        *rabbitmq_rules.rules(),
        *redis_rules.rules(),
        *st2cluster_rules.rules(),
        *system_user_rules.rules(),
    ]
