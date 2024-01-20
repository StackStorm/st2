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
from pack_metadata import tailor, target_types_rules
from pack_metadata.target_types import (
    PackMetadata,
    PackMetadataInGitSubmodule,
    PacksGlob,
)


def rules():
    return [
        *tailor.rules(),
        *target_types_rules.rules(),
    ]


def target_types():
    return [
        PackMetadata,
        PackMetadataInGitSubmodule,
        PacksGlob,
    ]
