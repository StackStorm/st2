# Copyright 2021 The StackStorm Authors.
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

"""
Micro benchmarks which benchmark our mongo escape and unescape function.

NOTE: We utilize JSON fixture files which also contain values even though escaping only operates
on the item keys.
"""

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import os
import json

import pytest

from st2common.util import mongoescape

from common import FIXTURES_DIR


@pytest.mark.parametrize(
    "fixture_file",
    [
        "tiny_1.json",
        "json_61kb.json",
        "json_647kb.json",
        "json_4mb.json",
        "json_8mb.json",
        "json_4mb_single_large_field.json",
    ],
    ids=[
        "tiny_1.json",
        "json_61kb.json",
        "json_647kb.json",
        "json_4mb.json",
        "json_8mb.json",
        "json_4mb_single_large_field.json",
    ],
)
@pytest.mark.benchmark(group="escape_chars")
def test_escape_chars(benchmark, fixture_file: str) -> None:
    with open(os.path.join(FIXTURES_DIR, fixture_file), "r") as fp:
        content = fp.read()

    data = json.loads(content)

    def run_benchmark():
        result = mongoescape.escape_chars(data)
        return result

    escaped_data = benchmark(run_benchmark)
    unescaped_data = mongoescape.unescape_chars(escaped_data)
    assert escaped_data != data
    assert unescaped_data == data


@pytest.mark.parametrize(
    "fixture_file",
    [
        "tiny_1.json",
        "json_61kb.json",
        "json_647kb.json",
        "json_4mb.json",
        "json_8mb.json",
        "json_4mb_single_large_field.json",
    ],
    ids=[
        "tiny_1.json",
        "json_61kb.json",
        "json_647kb.json",
        "json_4mb.json",
        "json_8mb.json",
        "json_4mb_single_large_field.json",
    ],
)
@pytest.mark.benchmark(group="unescape_chars")
def test_unescape_chars(benchmark, fixture_file: str) -> None:
    with open(os.path.join(FIXTURES_DIR, fixture_file), "r") as fp:
        content = fp.read()

    data = json.loads(content)
    escaped_data = mongoescape.escape_chars(data)

    def run_benchmark():
        result = mongoescape.unescape_chars(escaped_data)
        return result

    unescaped_data = benchmark(run_benchmark)
    escaped_data = mongoescape.escape_chars(escaped_data)
    assert unescaped_data != escaped_data
