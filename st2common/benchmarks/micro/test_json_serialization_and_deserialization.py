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

import os
import json
import simplejson

import pytest
import ujson
import orjson

from st2common.util.jsonify import json_encode_orjson

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.abspath(os.path.join(BASE_DIR, "../fixtures/json"))


@pytest.mark.parametrize(
    "implementation",
    ["json", "simplejson", "ujson", "orjson"],
    ids=[
        "json",
        "simplejson",
        "ujson",
        "orjson",
    ],
)
@pytest.mark.parametrize(
    "indent_sort_keys_tuple",
    [(0, False), (0, True), (2, False), (2, True)],
    ids=[
        "indent_none_sort_keys_false",
        "indent_none_sort_keys_true",
        "indent_2_sort_keys_false",
        "indent_2_sort_keys_true",
    ],
)
@pytest.mark.parametrize(
    "fixture_file",
    [
        "rows.json",
    ],
    ids=[
        "rows.json",
    ],
)
@pytest.mark.benchmark(group="json_dumps")
def test_json_dumps(benchmark, fixture_file, indent_sort_keys_tuple, implementation):
    indent, sort_keys = indent_sort_keys_tuple

    if not indent:
        separators = (",", ":")
    else:
        separators = None

    with open(os.path.join(FIXTURES_DIR, fixture_file), "r") as fp:
        content = fp.read()

    data = json.loads(content)

    def run_benchmark():
        if implementation == "json":
            return json.dumps(
                data, indent=indent, separators=separators, sort_keys=sort_keys
            )
        elif implementation == "simplejson":
            return simplejson.dumps(
                data, indent=indent, separators=separators, sort_keys=sort_keys
            )
        elif implementation == "ujson":
            return ujson.dumps(data, indent=indent, sort_keys=sort_keys)
        elif implementation == "orjson":
            return json_encode_orjson(data, indent=indent, sort_keys=sort_keys)
        else:
            raise ValueError("Invalid implementation: %s" % (implementation))

    result = benchmark.pedantic(run_benchmark, iterations=5, rounds=5)
    assert len(result) >= 40000


@pytest.mark.parametrize(
    "implementation",
    ["json", "simplejson", "ujson", "orjson"],
    ids=[
        "json",
        "simplejson",
        "ujson",
        "orjson",
    ],
)
@pytest.mark.parametrize(
    "fixture_file",
    [
        "rows.json",
    ],
    ids=[
        "rows.json",
    ],
)
@pytest.mark.benchmark(group="json_dumps")
def test_json_loads(benchmark, fixture_file, implementation):
    with open(os.path.join(FIXTURES_DIR, fixture_file), "r") as fp:
        content = fp.read()

    content_loaded = json.loads(content)

    def run_benchmark():
        if implementation == "json":
            return json.loads(content)
        elif implementation == "simplejson":
            return simplejson.loads(content)
        elif implementation == "ujson":
            return ujson.loads(content)
        elif implementation == "orjson":
            return orjson.loads(content)
        else:
            raise ValueError("Invalid implementation: %s" % (implementation))

    result = benchmark.pedantic(run_benchmark, iterations=10, rounds=10)
    assert result == content_loaded
