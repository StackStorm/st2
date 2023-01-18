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

from textwrap import dedent

import pytest

from pants.backend.python.target_types import (
    EntryPoint,
    PythonSourceTarget,
    PythonSourcesGeneratorTarget,
)
from pants.backend.python.target_types_rules import rules as python_target_types_rules
from pants.engine.addresses import Address
from pants.engine.internals.scheduler import ExecutionError
from pants.engine.target import InferredDependencies
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .target_types_rules import (
    InferStevedoreExtensionDependencies,
    StevedoreEntryPointsInferenceFieldSet,
    resolve_stevedore_entry_points,
    rules as stevedore_target_types_rules,
)
from .target_types import (
    ResolveStevedoreEntryPointsRequest,
    ResolvedStevedoreEntryPoints,
    StevedoreEntryPoint,
    StevedoreEntryPointsField,  # on stevedore_extension target
    StevedoreExtension,
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


def test_infer_stevedore_entry_points_dependencies() -> None:
    rule_runner = RuleRunner(
        rules=[
            *python_target_types_rules(),
            *stevedore_target_types_rules(),
            QueryRule(InferredDependencies, (InferStevedoreExtensionDependencies,)),
        ],
        target_types=[
            PythonSourceTarget,
            PythonSourcesGeneratorTarget,
            StevedoreExtension,
        ],
    )
    rule_runner.write_files(
        {
            "runners/foobar_runner/BUILD": dedent(
                """\
                stevedore_extension(
                    name="runner",
                    namespace="st2common.runners.runner",
                    entry_points={
                        "foobar": "foobar_runner.foobar_runner",
                    },
                )

                stevedore_extension(
                    name="foobar",
                    namespace="example.foobar",
                    entry_points={
                        "thing1": "foobar_runner.thing1:ThingBackend",
                        "thing2": "foobar_runner.thing2:ThingBackend",
                    },
                )
                """
            ),
            "runners/foobar_runner/foobar_runner/BUILD": "python_sources()",
            "runners/foobar_runner/foobar_runner/__init__.py": "",
            "runners/foobar_runner/foobar_runner/foobar_runner.py": "",
            "runners/foobar_runner/foobar_runner/thing1.py": dedent(
                """\
                class ThingBackend:
                    pass
                """
            ),
            "runners/foobar_runner/foobar_runner/thing2.py": dedent(
                """\
                class ThingBackend:
                    pass
                """
            ),
        }
    )

    def run_dep_inference(address: Address) -> InferredDependencies:
        args = [
            "--source-root-patterns=runners/*_runner",
            "--python-infer-assets",
        ]
        rule_runner.set_options(args, env_inherit={"PATH", "PYENV_ROOT", "HOME"})
        target = rule_runner.get_target(address)
        return rule_runner.request(
            InferredDependencies,
            [
                InferStevedoreExtensionDependencies(
                    StevedoreEntryPointsInferenceFieldSet.create(target)
                )
            ],
        )

    assert run_dep_inference(
        Address("runners/foobar_runner", target_name="runner")
    ) == InferredDependencies(
        [
            Address(
                "runners/foobar_runner/foobar_runner",
                relative_file_path="foobar_runner.py",
            ),
        ],
    )

    assert run_dep_inference(
        Address("runners/foobar_runner", target_name="foobar")
    ) == InferredDependencies(
        [
            Address(
                "runners/foobar_runner/foobar_runner",
                relative_file_path="thing1.py",
            ),
            Address(
                "runners/foobar_runner/foobar_runner",
                relative_file_path="thing2.py",
            ),
        ],
    )
