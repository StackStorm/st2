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

from pants.backend.python.target_types import (
    PythonSourceTarget,
    PythonSourcesGeneratorTarget,
)
from pants.backend.python.target_types_rules import rules as python_target_types_rules
from pants.engine.addresses import Address
from pants.engine.target import InferredDependencies
from pants.testutil.rule_runner import QueryRule, RuleRunner

from .target_types_rules import (
    InferPacksGlobDependencies,
    PacksGlobInferenceFieldSet,
    rules as pack_metadata_target_types_rules,
)
from .target_types import PacksGlob


def test_infer_packs_globs_dependencies() -> None:
    rule_runner = RuleRunner(
        rules=[
            *python_target_types_rules(),
            *pack_metadata_target_types_rules(),
            QueryRule(InferredDependencies, (InferPacksGlobDependencies,)),
        ],
        target_types=[
            PythonSourceTarget,
            PythonSourcesGeneratorTarget,
            PacksGlob,
        ],
    )
    rule_runner.write_files(
        {
            "packs/BUILD": dedent(
                """\
                python_sources(
                    name="git_submodule",
                    sources=["./git_submodule/*.py"],
                )

                packs_glob(
                    name="all_packs_glob",
                    dependencies=[
                        "!./configs",  # explicit ignore
                        "./a",         # explicit include
                    ],
                )
                """
            ),
            "packs/a/BUILD": "python_sources()",
            "packs/a/__init__.py": "",
            "packs/a/fixture.py": "",
            "packs/b/BUILD": dedent(
                """\
                python_sources(
                    dependencies=["packs/configs/b.yaml"],
                )
                """
            ),
            "packs/b/__init__.py": "",
            "packs/b/fixture.py": "",
            "packs/c/BUILD": "python_sources()",
            "packs/c/__init__.py": "",
            "packs/c/fixture.py": "",
            "packs/d/BUILD": "python_sources()",
            "packs/d/__init__.py": "",
            "packs/d/fixture.py": "",
            # imitate a pack in a git submodule (should NOT have a BUILD file)
            "packs/git_submodule/__init__.py": "",
            "packs/git_submodule/fixture.py": "",
            "packs/configs/BUILD": dedent(
                """\
                resources(
                    sources=["*.yaml"],
                )
                """
            ),
            "packs/configs/b.yaml": dedent(
                """\
                ---
                # pack config for pack b
                """
            ),
        }
    )

    def run_dep_inference(address: Address) -> InferredDependencies:
        args = [
            "--source-root-patterns=/packs",
        ]
        rule_runner.set_options(args, env_inherit={"PATH", "PYENV_ROOT", "HOME"})
        target = rule_runner.get_target(address)
        return rule_runner.request(
            InferredDependencies,
            [InferPacksGlobDependencies(PacksGlobInferenceFieldSet.create(target))],
        )

    assert run_dep_inference(
        Address("packs", target_name="all_packs_glob")
    ) == InferredDependencies(
        [
            # should not have packs/a (explicit dep does not need to be inferred)
            # should not have packs/configs (explicitly ignored)
            # should not have packs/git_submodule (no BUILD file = no targets to add)
            Address("packs/b"),
            Address("packs/c"),
            Address("packs/d"),
        ],
    )
