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

from pants.backend.python.goals.setup_py import SetupKwargs, SetupKwargsRequest
from pants.backend.python.macros.python_artifact import PythonArtifact
from pants.backend.python.target_types import (
    PythonDistribution,
    PythonSourceTarget,
    PythonSourcesGeneratorTarget,
)
from pants.backend.python.target_types_rules import rules as python_target_types_rules
from pants.engine.addresses import Address
from pants.engine.rules import rule
from pants.engine.target import Target
from pants.testutil.rule_runner import QueryRule, RuleRunner
from pants.util.frozendict import FrozenDict

from release.rules import StackStormSetupKwargsRequest
from release.rules import rules as release_rules


@pytest.fixture
def rule_runner() -> RuleRunner:
    rule_runner = RuleRunner(
        rules=[
            *python_target_types_rules(),
            *release_rules(),
            QueryRule(SetupKwargs, (StackStormSetupKwargsRequest,)),
        ],
        target_types=[
            PythonDistribution,
            PythonSourceTarget,
            PythonSourcesGeneratorTarget,
        ],
        objects={"python_artifact": PythonArtifact},
    )
    rule_runner.write_files(
        {
            "runners/foobar_runner/BUILD": dedent(
                """\
                python_distribution(
                    provides=python_artifact(
                        name="stackstorm-runner-foobar",
                    ),
                    dependencies=["./foobar_runner"],
                    entry_points={
                        "st2common.runners.runner": {
                            "foobar": "foobar_runner.foobar_runner",
                        },
                    },
                )
                """
            ),
            "runners/foobar_runner/foobar_runner/BUILD": "python_sources()",
            "runners/foobar_runner/foobar_runner/__init__.py": "",
            "runners/foobar_runner/foobar_runner/foobar_runner.py": "",
            "runners/foobar_runner/foobar_runner/thing1.py": "",
            "runners/foobar_runner/foobar_runner/thing2.py": "",
        }
    )
    args = [
        "--source-root-patterns=runners/*_runner",
    ]
    rule_runner.set_options(args, env_inherit={"PATH", "PYENV_ROOT", "HOME"})
    return rule_runner


def gen_setup_kwargs(address: Address, rule_runner: RuleRunner) -> SetupKwargs:
    target = rule_runner.get_target(address)
    return rule_runner.request(
        SetupKwargs,
        [StackStormSetupKwargsRequest(target)],
    )


def test_setup_kwargs_plugin(rule_runner: RuleRunner) -> None:

    address = Address("runners/foobar_runner")
    assert gen_setup_kwargs(address, rule_runner) == SetupKwargs(
        FrozenDict(
            {
                "entry_points": FrozenDict(
                    {
                        "st2common.runners.runner": (
                            "foobar = foobar_runner.foobar_runner",
                        ),
                    }
                )
            }
        ),
        address=address,
    )
