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

from dataclasses import dataclass
from typing import Set

from pants.backend.python.goals.pytest_runner import (
    PytestPluginSetupRequest,
    PytestPluginSetup,
)
from pants.engine.internals.native_engine import Address
from pants.engine.rules import collect_rules, Get, MultiGet, rule
from pants.engine.target import Target, TransitiveTargets, TransitiveTargetsRequest
from pants.engine.unions import UnionRule
from pants.util.logging import LogLevel
from pants.util.ordered_set import OrderedSet

from pack_metadata.python_rules.python_pack_content import (
    PackContentPythonEntryPoints,
    PackContentPythonEntryPointsRequest,
    PackPythonLibs,
    PackPythonLibsRequest,
)
from pack_metadata.target_types import InjectPackPythonPathField


@dataclass(frozen=True)
class PackPythonPath:
    entries: tuple[str, ...] = ()


@dataclass(frozen=True)
class PackPythonPathRequest:
    address: Address


@rule(
    desc="Get pack paths that should be added to PYTHONPATH/PEX_EXTRA_SYS_PATH for a target.",
    level=LogLevel.DEBUG,
)
async def get_extra_sys_path_for_pack_dependencies(
    request: PackPythonPathRequest,
) -> PackPythonPath:
    transitive_targets = await Get(
        TransitiveTargets, TransitiveTargetsRequest((request.address,))
    )

    dependency_addresses: Set[Address] = {
        tgt.address for tgt in transitive_targets.closure
    }
    if not dependency_addresses:
        return PackPythonPath()

    pack_content_python_entry_points, pack_python_libs = await MultiGet(
        Get(PackContentPythonEntryPoints, PackContentPythonEntryPointsRequest()),
        Get(PackPythonLibs, PackPythonLibsRequest()),
    )

    # only use addresses of actual dependencies
    pack_python_content_addresses: Set[Address] = dependency_addresses & {
        pack_content.python_address for pack_content in pack_content_python_entry_points
    }
    pack_python_lib_addresses: Set[Address] = dependency_addresses & {
        pack_lib.python_address for pack_lib in pack_python_libs
    }

    if not (pack_python_content_addresses or pack_python_lib_addresses):
        return PackPythonPath()

    # filter pack_content_python_entry_points and pack_python_libs
    pack_content_python_entry_points = (
        pack_content
        for pack_content in pack_content_python_entry_points
        if pack_content.python_address in pack_python_content_addresses
    )
    pack_python_libs = (
        pack_lib
        for pack_lib in pack_python_libs
        if pack_lib.python_address in pack_python_lib_addresses
    )

    extra_sys_path_entries = OrderedSet()
    for pack_content in pack_content_python_entry_points:
        for path_entry in pack_content.get_possible_paths():
            extra_sys_path_entries.add(path_entry)
    for pack_lib in pack_python_libs:
        extra_sys_path_entries.add(pack_lib.lib_path.as_posix())

    return PackPythonPath(tuple(extra_sys_path_entries))


class PytestPackTestRequest(PytestPluginSetupRequest):
    @classmethod
    def is_applicable(cls, target: Target) -> bool:
        if not target.has_field(InjectPackPythonPathField):
            return False
        return bool(target.get(InjectPackPythonPathField).value)


@rule(
    desc="Inject pack paths in PYTHONPATH/PEX_EXTRA_SYS_PATH for python tests.",
    level=LogLevel.DEBUG,
)
async def inject_extra_sys_path_for_pack_tests(
    request: PytestPackTestRequest,
) -> PytestPluginSetup:
    pack_python_path = await Get(
        PackPythonPath, PackPythonPathRequest(request.target.address)
    )
    return PytestPluginSetup(
        # digest=EMPTY_DIGEST,
        extra_sys_path=pack_python_path.entries,
    )


def rules():
    return [
        *collect_rules(),
        UnionRule(PytestPluginSetupRequest, PytestPackTestRequest),
    ]
