# Copyright 2024 The StackStorm Authors.
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
from collections import defaultdict
from typing import DefaultDict

from pants.backend.python.dependency_inference.module_mapper import (
    FirstPartyPythonMappingImpl,
    FirstPartyPythonMappingImplMarker,
    ModuleProvider,
    ModuleProviderType,
    ResolveName,
)
from pants.engine.rules import Get, MultiGet, collect_rules, rule
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel

from pack_metadata.python_rules.python_pack_content import (
    PackContentPythonEntryPoints,
    PackContentPythonEntryPointsRequest,
    PackPythonLibs,
    PackPythonLibsRequest,
)
from pack_metadata.target_types import PackMetadata


# This is only used to register our implementation with the plugin hook via unions.
class St2PythonPackContentMappingMarker(FirstPartyPythonMappingImplMarker):
    pass


@rule(
    desc=f"Creating map of `{PackMetadata.alias}` targets to Python modules in pack content",
    level=LogLevel.DEBUG,
)
async def map_pack_content_to_python_modules(
    _: St2PythonPackContentMappingMarker,
) -> FirstPartyPythonMappingImpl:
    resolves_to_modules_to_providers: DefaultDict[
        ResolveName, DefaultDict[str, list[ModuleProvider]]
    ] = defaultdict(lambda: defaultdict(list))

    pack_content_python_entry_points = await Get(
        PackContentPythonEntryPoints,
        PackContentPythonEntryPointsRequest(),
    )

    for pack_content in pack_content_python_entry_points:
        resolves_to_modules_to_providers[pack_content.resolve][
            pack_content.module
        ].append(ModuleProvider(pack_content.python_address, ModuleProviderType.IMPL))

    return FirstPartyPythonMappingImpl.create(resolves_to_modules_to_providers)


def rules():
    return (
        *collect_rules(),
        UnionRule(FirstPartyPythonMappingImplMarker, St2PythonPackContentMappingMarker),
    )
