# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
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

NOTE: We utiliz JSON fixture files which also contain values even though escaping only operates
on the item keys.
"""

import os
import json

import pytest

from st2common.util import mongoescape

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.abspath(os.path.join(BASE_DIR, "../fixtures/json"))


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

    escaped_data = benchmark.pedantic(run_benchmark, iterations=10, rounds=10)
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

    unescaped_data = benchmark.pedantic(run_benchmark, iterations=10, rounds=10)
    escaped_data = mongoescape.escape_chars(escaped_data)
    assert unescaped_data != escaped_data
