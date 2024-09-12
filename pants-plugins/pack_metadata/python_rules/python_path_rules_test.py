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

import pytest
from pants.backend.python.goals.pytest_runner import PytestPluginSetup
from pants.engine.internals.native_engine import Address, EMPTY_DIGEST
from pants.testutil.rule_runner import RuleRunner

from pack_metadata.python_rules.python_path_rules import (
    PackPythonPath,
    PackPythonPathRequest,
    PytestPackTestRequest,
)


@pytest.mark.parametrize(
    "address,expected",
    (
        (
            Address("packs/foo/actions", relative_file_path="get_bar.py"),
            ("packs/foo/actions",),
        ),
        (
            Address("packs/foo/actions", relative_file_path="get_baz.py"),
            ("packs/foo/actions",),
        ),
        (
            Address("packs/foo/tests", relative_file_path="test_get_bar_action.py"),
            ("packs/foo/actions",),
        ),
        (
            Address("packs/foo/tests", relative_file_path="test_get_baz_action.py"),
            ("packs/foo/actions",),
        ),
        (
            Address(
                "packs/dr_seuss/actions/lib/seuss", relative_file_path="__init__.py"
            ),
            ("packs/dr_seuss/actions/lib",),
        ),
        (
            Address("packs/dr_seuss/actions/lib/seuss", relative_file_path="things.py"),
            ("packs/dr_seuss/actions/lib",),
        ),
        (
            Address(
                "packs/dr_seuss/actions", relative_file_path="get_from_actions_lib.py"
            ),
            ("packs/dr_seuss/actions", "packs/dr_seuss/actions/lib"),
        ),
        (
            Address(
                "packs/dr_seuss/tests",
                relative_file_path="test_get_from_actions_lib_action.py",
            ),
            ("packs/dr_seuss/actions", "packs/dr_seuss/actions/lib"),
        ),
        (
            Address(
                "packs/shards/lib/stormlight_archive", relative_file_path="__init__.py"
            ),
            ("packs/shards/lib",),
        ),
        (
            Address(
                "packs/shards/lib/stormlight_archive", relative_file_path="things.py"
            ),
            ("packs/shards/lib",),
        ),
        (
            Address("packs/shards/actions", relative_file_path="get_from_pack_lib.py"),
            ("packs/shards/actions", "packs/shards/lib"),
        ),
        (
            Address("packs/shards/sensors", relative_file_path="horn_eater.py"),
            ("packs/shards/sensors", "packs/shards/lib"),
        ),
        (
            Address(
                "packs/shards/tests",
                relative_file_path="test_get_from_pack_lib_action.py",
            ),
            ("packs/shards/actions", "packs/shards/lib"),
        ),
        (
            Address(
                "packs/shards/tests", relative_file_path="test_horn_eater_sensor.py"
            ),
            ("packs/shards/sensors", "packs/shards/lib"),
        ),
        (
            Address("packs/metals/actions/mist_born", relative_file_path="__init__.py"),
            (),  # there are no dependencies, and this is not an action entry point.
        ),
        (
            Address("packs/metals/actions/mist_born", relative_file_path="fly.py"),
            ("packs/metals/actions/mist_born", "packs/metals/actions"),
        ),
        (
            Address("packs/metals/tests", relative_file_path="test_fly_action.py"),
            ("packs/metals/actions/mist_born", "packs/metals/actions"),
        ),
    ),
)
def test_get_extra_sys_path_for_pack_dependencies(
    rule_runner: RuleRunner, address: Address, expected: tuple[str, ...]
) -> None:
    pack_python_path = rule_runner.request(
        PackPythonPath, (PackPythonPathRequest(address),)
    )
    assert pack_python_path.entries == expected


@pytest.mark.xfail(raises=AttributeError, reason="Not implemented in pants yet.")
@pytest.mark.parametrize(
    "address,expected",
    (
        (
            Address("packs/foo/tests", relative_file_path="test_get_bar_action.py"),
            ("packs/foo/actions",),
        ),
        (
            Address("packs/foo/tests", relative_file_path="test_get_baz_action.py"),
            ("packs/foo/actions",),
        ),
        (
            Address(
                "packs/dr_seuss/tests",
                relative_file_path="test_get_from_actions_lib_action.py",
            ),
            ("packs/dr_seuss/actions", "packs/dr_seuss/actions/lib"),
        ),
        (
            Address(
                "packs/shards/tests",
                relative_file_path="test_get_from_pack_lib_action.py",
            ),
            ("packs/shards/actions", "packs/shards/lib"),
        ),
        (
            Address(
                "packs/shards/tests", relative_file_path="test_horn_eater_sensor.py"
            ),
            ("packs/shards/sensors", "packs/shards/lib"),
        ),
        (
            Address("packs/metals/tests", relative_file_path="test_fly_action.py"),
            ("packs/metals/actions/mist_born", "packs/metals/actions"),
        ),
    ),
)
def test_inject_extra_sys_path_for_pack_tests(
    rule_runner: RuleRunner, address: Address, expected: tuple[str, ...]
) -> None:
    target = rule_runner.get_target(address)
    result = rule_runner.request(PytestPluginSetup, (PytestPackTestRequest(target),))
    assert result.digest == EMPTY_DIGEST
    assert result.extra_sys_path == expected
