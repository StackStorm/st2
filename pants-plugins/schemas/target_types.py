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
from pants.engine.fs import GlobMatchErrorBehavior
from pants.engine.target import (
    COMMON_TARGET_FIELDS,
    Dependencies,
    MultipleSourcesField,
    Target,
    generate_multiple_sources_field_help_message,
)


class SchemasSourcesField(MultipleSourcesField):
    expected_file_extensions = (".json",)
    default = ("*.json",)
    uses_source_roots = False

    # make sure at least one schema is present or fmt will be skipped.
    default_glob_match_error_behavior = GlobMatchErrorBehavior.error

    help = generate_multiple_sources_field_help_message(
        "Example: `sources=['*.json', '!ignore.json']`"
    )


class Schemas(Target):
    alias = "schemas"
    core_fields = (*COMMON_TARGET_FIELDS, Dependencies, SchemasSourcesField)
    help = (
        "Generate st2 metadata (pack, action, rule, ...) schemas from python sources."
    )
