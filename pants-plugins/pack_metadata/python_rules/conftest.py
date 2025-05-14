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

from textwrap import dedent

import pytest
from pants.backend.python.dependency_inference.module_mapper import (
    FirstPartyPythonMappingImpl,
)
from pants.backend.python.goals.pytest_runner import PytestPluginSetup
from pants.backend.python.target_types import (
    PythonSourceTarget,
    PythonSourcesGeneratorTarget,
    PythonTestTarget,
    PythonTestsGeneratorTarget,
)
from pants.backend.python.target_types_rules import rules as python_target_types_rules
from pants.engine.rules import QueryRule
from pants.testutil.python_rule_runner import PythonRuleRunner
from pants.testutil.rule_runner import RuleRunner

from pack_metadata.python_rules import (
    python_module_mapper,
    python_pack_content,
    python_path_rules,
)
from pack_metadata.python_rules.python_module_mapper import (
    St2PythonPackContentMappingMarker,
)
from pack_metadata.python_rules.python_pack_content import (
    PackContentPythonEntryPoints,
    PackContentPythonEntryPointsRequest,
    PackContentResourceTargetsOfType,
    PackContentResourceTargetsOfTypeRequest,
    PackPythonLibs,
    PackPythonLibsRequest,
)
from pack_metadata.python_rules.python_path_rules import (
    PackPythonPath,
    PackPythonPathRequest,
    PytestPackTestRequest,
)
from pack_metadata.target_types import (
    InjectPackPythonPathField,
    PackContentResourceTarget,
    PackMetadata,
)

# some random pack names
packs = (
    "foo",  # imports between actions
    "dr_seuss",  # imports from <pack>/actions/lib
    "shards",  # imports from <pack>/lib
    "metals",  # imports the action from a subdirectory
)


@pytest.fixture
def pack_names() -> tuple[str, ...]:
    return packs


def write_test_files(rule_runner: RuleRunner):
    for pack in packs:
        rule_runner.write_files(
            {
                f"packs/{pack}/BUILD": dedent(
                    """
                    __defaults__(all=dict(inject_pack_python_path=True))
                    pack_metadata(name="metadata")
                    """
                ),
                f"packs/{pack}/pack.yaml": dedent(
                    f"""
                    ---
                    name: {pack}
                    version: 1.0.0
                    author: StackStorm
                    email: info@stackstorm.com
                    """
                ),
                f"packs/{pack}/config.schema.yaml": "",
                f"packs/{pack}/config.yaml.example": "",
                f"packs/{pack}/icon.png": "",
                f"packs/{pack}/README.md": f"# Pack {pack} README",
            }
        )

    def action_metadata_file(action: str, entry_point: str = "") -> str:
        entry_point = entry_point or f"{action}.py"
        return dedent(
            f"""
            ---
            name: {action}
            runner_type: python-script
            entry_point: {entry_point}
            """
        )

    def test_file(module: str, _object: str) -> str:
        return dedent(
            f"""
            from {module} import {_object}
            def test_{module.replace(".", "_")}() -> None:
                pass
            """
        )

    rule_runner.write_files(
        {
            "packs/foo/actions/BUILD": "python_sources()",
            "packs/foo/actions/get_bar.yaml": action_metadata_file("get_bar"),
            "packs/foo/actions/get_bar.py": dedent(
                """
                RESPONSE_CONSTANT = "foobar_key"
                class BarAction:
                    def run(self):
                        return {RESPONSE_CONSTANT: "bar"}
                """
            ),
            "packs/foo/actions/get_baz.yaml": action_metadata_file("get_baz"),
            "packs/foo/actions/get_baz.py": dedent(
                """
                from get_bar import RESPONSE_CONSTANT
                class BazAction:
                    def run(self):
                        return {RESPONSE_CONSTANT: "baz"}
                """
            ),
            "packs/foo/tests/BUILD": "python_tests()",
            "packs/foo/tests/test_get_bar_action.py": test_file("get_bar", "BarAction"),
            "packs/foo/tests/test_get_baz_action.py": test_file("get_baz", "BazAction"),
            "packs/dr_seuss/actions/lib/seuss/BUILD": "python_sources()",
            "packs/dr_seuss/actions/lib/seuss/__init__.py": "",
            "packs/dr_seuss/actions/lib/seuss/things.py": dedent(
                """
                THING1 = "thing one"
                THING2 = "thing two"
                """
            ),
            "packs/dr_seuss/actions/BUILD": "python_sources()",
            "packs/dr_seuss/actions/get_from_actions_lib.yaml": action_metadata_file(
                "get_from_actions_lib"
            ),
            "packs/dr_seuss/actions/get_from_actions_lib.py": dedent(
                """
                from seuss.things import THING1, THING2
                class GetFromActionsLibAction:
                    def run(self):
                        return {"things": (THING1, THING2)}
                """
            ),
            "packs/dr_seuss/tests/BUILD": "python_tests()",
            "packs/dr_seuss/tests/test_get_from_actions_lib_action.py": test_file(
                "get_from_actions_lib", "GetFromActionsLibAction"
            ),
            "packs/shards/lib/stormlight_archive/BUILD": "python_sources()",
            "packs/shards/lib/stormlight_archive/__init__.py": "",
            "packs/shards/lib/stormlight_archive/things.py": dedent(
                """
                STORM_LIGHT = "Honor"
                VOID_LIGHT = "Odium"
                LIFE_LIGHT = "Cultivation"
                """
            ),
            "packs/shards/actions/BUILD": "python_sources()",
            "packs/shards/actions/get_from_pack_lib.yaml": action_metadata_file(
                "get_from_pack_lib"
            ),
            "packs/shards/actions/get_from_pack_lib.py": dedent(
                """
                from stormlight_archive.things import STORM_LIGHT, VOID_LIGHT, LIFE_LIGHT
                class GetFromPackLibAction:
                    def run(self):
                        return {"light_sources": (STORM_LIGHT, VOID_LIGHT, LIFE_LIGHT)}
                """
            ),
            "packs/shards/sensors/BUILD": "python_sources()",
            "packs/shards/sensors/horn_eater.yaml": dedent(
                """
                ---
                name: horn_eater
                entry_point: horn_eater.py
                class_name: HornEaterSensor
                trigger_types: [{name: horn_eater.saw.spren, payload_schema: {type: object}}]
                """
            ),
            "packs/shards/sensors/horn_eater.py": dedent(
                """
                from st2reactor.sensor.base import PollingSensor
                from stormlight_archive.things import STORM_LIGHT
                class HornEaterSensor(PollingSensor):
                    def setup(self): pass
                    def poll(self):
                        if STORM_LIGHT in self.config:
                            self.sensor_service.dispatch(
                                trigger="horn_eater.saw.spren", payload={"spren_type": STORM_LIGHT}
                            )
                    def cleanup(self): pass
                    def add_trigger(self): pass
                    def update_trigger(self): pass
                    def remove_trigger(self): pass
                """
            ),
            "packs/shards/tests/BUILD": "python_tests()",
            "packs/shards/tests/test_get_from_pack_lib_action.py": test_file(
                "get_from_pack_lib", "GetFromPackLibAction"
            ),
            "packs/shards/tests/test_horn_eater_sensor.py": test_file(
                "horn_eater", "HornEaterSensor"
            ),
            "packs/metals/actions/fly.yaml": action_metadata_file(
                "fly", "mist_born/fly.py"
            ),
            "packs/metals/actions/mist_born/BUILD": "python_sources()",
            "packs/metals/actions/mist_born/__init__.py": "",
            "packs/metals/actions/mist_born/fly.py": dedent(
                """
                class FlyAction:
                    def run(self):
                        return {"metals": ("steel", "iron")}
                """
            ),
            "packs/metals/tests/BUILD": "python_tests()",
            "packs/metals/tests/test_fly_action.py": test_file(
                "mist_born.fly", "FlyAction"
            ),
        }
    )


@pytest.fixture
def rule_runner() -> RuleRunner:
    rule_runner = PythonRuleRunner(
        rules=[
            PythonTestsGeneratorTarget.register_plugin_field(
                InjectPackPythonPathField, as_moved_field=True
            ),
            PythonTestTarget.register_plugin_field(InjectPackPythonPathField),
            *python_target_types_rules(),
            # TODO: not sure if we need a QueryRule for every rule...
            *python_pack_content.rules(),
            QueryRule(
                PackContentResourceTargetsOfType,
                (PackContentResourceTargetsOfTypeRequest,),
            ),
            QueryRule(
                PackContentPythonEntryPoints, (PackContentPythonEntryPointsRequest,)
            ),
            QueryRule(PackPythonLibs, (PackPythonLibsRequest,)),
            *python_module_mapper.rules(),
            QueryRule(
                FirstPartyPythonMappingImpl, (St2PythonPackContentMappingMarker,)
            ),
            *python_path_rules.rules(),
            QueryRule(PackPythonPath, (PackPythonPathRequest,)),
            QueryRule(PytestPluginSetup, (PytestPackTestRequest,)),
        ],
        target_types=[
            PackContentResourceTarget,
            PackMetadata,
            PythonSourceTarget,
            PythonSourcesGeneratorTarget,
            PythonTestTarget,
            PythonTestsGeneratorTarget,
        ],
    )
    write_test_files(rule_runner)
    args = ["--source-root-patterns=packs/*"]
    rule_runner.set_options(args, env_inherit={"PATH", "PYENV_ROOT", "HOME"})
    return rule_runner
