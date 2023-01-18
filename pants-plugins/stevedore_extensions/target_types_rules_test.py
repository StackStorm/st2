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
from __future__ import annotations

import pytest

from pants.backend.python.target_types import (
    EntryPoint,
    PythonTestTarget,
    PythonTestsGeneratorTarget,
)
from pants.backend.python.target_types_rules import rules as python_target_types_rules
from pants.engine.addresses import Address
from pants.engine.internals.scheduler import ExecutionError
from pants.engine.target import InferDependenciesRequest, InferredDependencies, Target
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .target_types_rules import (
    InferStevedoreExtensionDependencies,
    resolve_stevedore_entry_points,
    rules as stevedore_target_types_rules,
)
from .target_types import (
    ResolveStevedoreEntryPointsRequest,
    ResolvedStevedoreEntryPoints,
    StevedoreEntryPoint,
    StevedoreEntryPoints,
    StevedoreEntryPointsField,  # on stevedore_extension target
    StevedoreExtension,
    StevedoreNamespaceField,  # on stevedore_extension target
    StevedoreNamespacesField,  # on other targets
)


def test_resolve_stevedore_entry_points() -> None:
    # based on: pants.backend.python.target_types_test.test_resolve_pex_binary_entry_point
    rule_runner = RuleRunner(
        rules=[
            resolve_stevedore_entry_points,
            QueryRule(
                ResolvedStevedoreEntryPoints, (ResolveStevedoreEntryPointsRequest,)
            ),
        ]
    )

    def assert_resolved(
        *, entry_point: str | None, expected: EntryPoint | None
    ) -> None:
        plugin_name = "plugin"
        addr = Address("src/python/project")
        rule_runner.write_files(
            {
                "src/python/project/app.py": "",
                "src/python/project/f2.py": "",
            }
        )
        ep_field = StevedoreEntryPointsField({plugin_name: entry_point}, addr)

        result = rule_runner.request(
            ResolvedStevedoreEntryPoints, [ResolveStevedoreEntryPointsRequest(ep_field)]
        )

        assert result.val is not None
        assert len(result.val) == 1
        assert result.val[0].name == plugin_name
        assert result.val[0].value == expected

    # Full module provided.
    assert_resolved(
        entry_point="custom.entry_point", expected=EntryPoint("custom.entry_point")
    )
    assert_resolved(
        entry_point="custom.entry_point:func",
        expected=EntryPoint.parse("custom.entry_point:func"),
    )

    # File names are expanded into the full module path.
    assert_resolved(entry_point="app.py", expected=EntryPoint(module="project.app"))
    assert_resolved(
        entry_point="app.py:func",
        expected=EntryPoint(module="project.app", function="func"),
    )

    with pytest.raises(ExecutionError):
        assert_resolved(
            entry_point="doesnt_exist.py", expected=EntryPoint("doesnt matter")
        )
    # Resolving >1 file is an error.
    with pytest.raises(ExecutionError):
        assert_resolved(entry_point="*.py", expected=EntryPoint("doesnt matter"))

    # Test with multiple entry points (keep indiviudual asserts above,
    # despite apparent duplication below, to simplify finding bugs).
    rule_runner.write_files(
        {
            "src/python/project/app.py": "",
            "src/python/project/f2.py": "",
        }
    )
    entry_points_field = StevedoreEntryPointsField(
        {
            "a": "custom.entry_point",
            "b": "custom.entry_point:func",
            "c": "app.py",
            "d": "app.py:func",
        },
        Address("src/python/project"),
    )

    resolved = rule_runner.request(
        ResolvedStevedoreEntryPoints,
        [ResolveStevedoreEntryPointsRequest(entry_points_field)],
    )

    assert resolved.val is not None
    assert set(resolved.val) == {
        StevedoreEntryPoint("a", EntryPoint(module="custom.entry_point")),
        StevedoreEntryPoint(
            "b", EntryPoint(module="custom.entry_point", function="func")
        ),
        StevedoreEntryPoint("c", EntryPoint(module="project.app")),
        StevedoreEntryPoint("d", EntryPoint(module="project.app", function="func")),
    }


# async def infer_stevedore_entry_points_dependencies(
#    request: InferStevedoreExtensionDependencies,
#    python_setup: PythonSetup,
# ) -> InferredDependencies:
#    Get ResolvedStevedoreEntryPoints


def test_infer_stevedore_entry_points_dependencies() -> None:
    rule_runner = RuleRunner(
        rules=[
            *python_target_types_rules(),
            *stevedore_target_types_rules(),
            QueryRule(
                ResolvedStevedoreEntryPoints, (ResolveStevedoreEntryPointsRequest,)
            ),
            QueryRule(InferredDependencies, (InferStevedoreExtensionDependencies,)),
        ],
        target_types=[
            PythonTestTarget,
            PythonTestsGeneratorTarget,
            StevedoreExtension,
        ],
    )
