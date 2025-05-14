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

from pants.backend.python.dependency_inference.module_mapper import (
    FirstPartyPythonMappingImpl,
    ModuleProvider,
    ModuleProviderType,
)
from pants.engine.internals.native_engine import Address
from pants.testutil.rule_runner import RuleRunner
from pants.util.frozendict import FrozenDict

from pack_metadata.python_rules.python_module_mapper import (
    St2PythonPackContentMappingMarker,
)


def test_map_pack_content_to_python_modules(rule_runner: RuleRunner) -> None:
    result = rule_runner.request(
        FirstPartyPythonMappingImpl,
        (St2PythonPackContentMappingMarker(),),
    )

    def module_provider(spec_path: str, relative_file_path: str) -> ModuleProvider:
        return ModuleProvider(
            Address(spec_path=spec_path, relative_file_path=relative_file_path),
            ModuleProviderType.IMPL,
        )

    expected = {
        "<ignore>": {
            "get_bar": (module_provider("packs/foo/actions", "get_bar.py"),),
            "get_baz": (module_provider("packs/foo/actions", "get_baz.py"),),
            "seuss": (
                module_provider("packs/dr_seuss/actions/lib/seuss", "__init__.py"),
            ),
            "seuss.things": (
                module_provider("packs/dr_seuss/actions/lib/seuss", "things.py"),
            ),
            "get_from_actions_lib": (
                module_provider("packs/dr_seuss/actions", "get_from_actions_lib.py"),
            ),
            "stormlight_archive": (
                module_provider("packs/shards/lib/stormlight_archive", "__init__.py"),
            ),
            "stormlight_archive.things": (
                module_provider("packs/shards/lib/stormlight_archive", "things.py"),
            ),
            "get_from_pack_lib": (
                module_provider("packs/shards/actions", "get_from_pack_lib.py"),
            ),
            "horn_eater": (module_provider("packs/shards/sensors", "horn_eater.py"),),
            "fly": (module_provider("packs/metals/actions/mist_born", "fly.py"),),
            "mist_born.fly": (
                module_provider("packs/metals/actions/mist_born", "fly.py"),
            ),
        }
    }
    assert isinstance(result, FrozenDict)
    assert all(isinstance(value, FrozenDict) for value in result.values())
    # pytest reports dict differences better than FrozenDict
    assert {resolve: dict(value) for resolve, value in result.items()} == expected
