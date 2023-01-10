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
from pants.backend.python.target_types import PythonResolveField
from pants.engine.target import (
    COMMON_TARGET_FIELDS,
    Dependencies,
    Target,
)
from pants.core.target_types import (
    ResourceSourceField,
)


class APISpecSourceField(ResourceSourceField):
    default = "openapi.yaml"


class APISpec(Target):
    alias = "api_spec"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        Dependencies,
        APISpecSourceField,
        # hack: work around an issue in the pylint backend that tries to
        # use this field on the api_spec target, possibly because
        # it depends on python files.
        PythonResolveField,
    )
    help = "Generate openapi.yaml file from Jinja2 template and python sources."
