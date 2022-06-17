# Copyright 2022 The StackStorm Authors.
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
from pants.engine.target import (
    COMMON_TARGET_FIELDS,
    Dependencies,
    SingleSourceField,
    Target,
)


class APISpecSourceField(SingleSourceField):
    default = "openapi.yaml"


class APISpec(Target):
    alias = "api_spec"
    core_fields = (*COMMON_TARGET_FIELDS, Dependencies, APISpecSourceField)
    help = "Generate openapi.yaml file from Jinja2 template and python sources."
