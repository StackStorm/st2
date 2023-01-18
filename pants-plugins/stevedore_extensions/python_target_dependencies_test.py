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
    PythonSourceTarget,
    PythonSourcesGeneratorTarget,
    PythonTestTarget,
    PythonTestsGeneratorTarget,
)
from pants.backend.python.target_types_rules import rules as python_target_types_rules
from pants.engine.addresses import Address
from pants.engine.target import InferredDependencies
from pants.testutil.rule_runner import QueryRule, RuleRunner
from pants.util.frozendict import FrozenDict

from .python_target_dependencies import (
    InferStevedoreNamespaceDependencies,
    PythonTestsStevedoreNamespaceInferenceFieldSet,
    StevedoreExtensions,
    rules as stevedore_dep_rules,
)
from .target_types import (
    AllStevedoreExtensionTargets,
    StevedoreExtension,
)


# random set of runner names to use in tests
st2_runners = ["noop", "python", "foobar"]


@pytest.fixture
def rule_runner() -> RuleRunner:
    rule_runner = RuleRunner(
        rules=[
            *python_target_types_rules(),
            *stevedore_dep_rules(),
            QueryRule(AllStevedoreExtensionTargets, ()),
            QueryRule(StevedoreExtensions, ()),
            QueryRule(InferredDependencies, (InferStevedoreNamespaceDependencies,)),
        ],
        target_types=[
            PythonSourceTarget,
            PythonSourcesGeneratorTarget,
            PythonTestTarget,
            PythonTestsGeneratorTarget,
            StevedoreExtension,
        ],
    )
    for runner in st2_runners:
        rule_runner.write_files(
            {
                f"runners/{runner}_runner/BUILD": dedent(
                    f"""\
                    stevedore_extension(
                        name="runner",
                        namespace="st2common.runners.runner",
                        entry_points={{
                            "{runner}": "{runner}_runner.{runner}_runner",
                        }},
                    )
                    stevedore_extension(
                        name="thing",
                        namespace="some.thing.else",
                        entry_points={{
                            "{runner}": "{runner}_runner.thing",
                        }},
                    )
                    """
                ),
                f"runners/{runner}_runner/{runner}_runner/BUILD": "python_sources()",
                f"runners/{runner}_runner/{runner}_runner/__init__.py": "",
                f"runners/{runner}_runner/{runner}_runner/{runner}_runner.py": "",
                f"runners/{runner}_runner/{runner}_runner/thing.py": "",
            }
        )
    args = [
        "--source-root-patterns=runners/*_runner",
    ]
    rule_runner.set_options(args, env_inherit={"PATH", "PYENV_ROOT", "HOME"})
    return rule_runner


# -----------------------------------------------------------------------------------------------
# Tests for utility rules
# -----------------------------------------------------------------------------------------------


def test_find_all_stevedore_extension_targets(rule_runner: RuleRunner) -> None:
    assert rule_runner.request(
        AllStevedoreExtensionTargets, []
    ) == AllStevedoreExtensionTargets(
        rule_runner.get_target(
            Address(f"runners/{runner}_runner", target_name=target_name)
        )
        for runner in sorted(st2_runners)
        for target_name in ["runner", "thing"]
    )


def test_map_stevedore_extensions(rule_runner: RuleRunner) -> None:
    assert rule_runner.request(StevedoreExtensions, []) == StevedoreExtensions(
        FrozenDict(
            {
                "some.thing.else": tuple(
                    rule_runner.get_target(
                        Address(f"runners/{runner}_runner", target_name="thing")
                    )
                    for runner in sorted(st2_runners)
                ),
                "st2common.runners.runner": tuple(
                    rule_runner.get_target(
                        Address(f"runners/{runner}_runner", target_name="runner")
                    )
                    for runner in sorted(st2_runners)
                ),
            }
        )
    )


# -----------------------------------------------------------------------------------------------
# Tests for dependency inference of python targets (python_tests, etc)
# -----------------------------------------------------------------------------------------------


def test_infer_stevedore_namespace_dependencies(rule_runner: RuleRunner) -> None:
    rule_runner.write_files(
        {
            "src/foobar/BUILD": dedent(
                """\
                python_tests(
                    name="tests",
                    stevedore_namespaces=["st2common.runners.runner"],
                )
                """
            ),
            "src/foobar/test_something.py": "",
        }
    )

    def run_dep_inference(address: Address) -> InferredDependencies:
        target = rule_runner.get_target(address)
        return rule_runner.request(
            InferredDependencies,
            [
                InferStevedoreNamespaceDependencies(
                    PythonTestsStevedoreNamespaceInferenceFieldSet.create(target)
                )
            ],
        )

    # this asserts that only the st2common.runners.runner namespace gets selected.
    assert run_dep_inference(
        Address(
            "src/foobar", target_name="tests", relative_file_path="test_something.py"
        ),
    ) == InferredDependencies(
        [
            Address(
                f"runners/{runner}_runner",
                target_name="runner",
            )
            for runner in st2_runners
        ],
    )
