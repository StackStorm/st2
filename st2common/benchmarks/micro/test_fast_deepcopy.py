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
Micro benchmark which compares the performance of our fast_deepcopy_dict implementation using
different underlying implementations (copy.deepcopy, ujson, orjson).
"""

# TODO: Also use actual orquesta context and execution fixture files which contain real life data
# with large text strings, different value types, etc.

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import os
import copy
import random
import json
import simplejson

import pytest
import ujson
import orjson

from common import FIXTURES_DIR


def generate_random_dict(keys_count=10, depth=1):
    """
    Generate a dictionary with fixed random values.
    """
    result = {}

    keys = list(range(0, keys_count))
    random.shuffle(keys)

    current = {}
    result = current

    for index in range(0, depth):
        current["depth_%s" % (index)] = {}

        current = current["depth_%s" % (index)]

        for key in keys:
            current["key_%s" % (key)] = "value_%s" % (key)

    return result


@pytest.mark.parametrize(
    "implementation",
    ["copy_deepcopy", "ujson", "orjson"],
    ids=[
        "copy_deepcopy",
        "ujson",
        "orjson",
    ],
)
@pytest.mark.parametrize(
    "dict_keys_count_and_depth",
    [
        (10, 1),
        (100, 1),
        (1000, 1),
        (10, 10),
        (100, 10),
        (1000, 10),
    ],
    ids=[
        "10_1_attributes",
        "100_1_attributes",
        "1000_1_attributes",
        "10_10_attributes",
        "100_10_attributes",
        "1000_10_attributes",
    ],
)
@pytest.mark.benchmark(group="fast_deepcopy")
def test_fast_deepcopy_with_dict_values(
    benchmark, dict_keys_count_and_depth, implementation
):
    dict_keys, dict_depth = dict_keys_count_and_depth
    data = generate_random_dict(keys_count=dict_keys, depth=dict_depth)

    def run_benchmark():
        if implementation == "copy_deepcopy":
            return copy.deepcopy(data)
        elif implementation == "ujson":
            return ujson.loads(ujson.dumps(data))
        elif implementation == "orjson":
            return orjson.loads(orjson.dumps(data))
        else:
            raise ValueError("Invalid implementation: %s" % (implementation))

    result = benchmark(run_benchmark)
    assert result == data, "Output is not the same as the input"


@pytest.mark.parametrize(
    "implementation",
    ["copy_deepcopy", "json", "simplejson", "ujson", "orjson"],
    ids=[
        "copy_deepcopy",
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
@pytest.mark.benchmark(group="fast_deepcopy")
def test_fast_deepcopy_with_json_fixture_file(benchmark, fixture_file, implementation):
    with open(os.path.join(FIXTURES_DIR, fixture_file), "r") as fp:
        content = fp.read()

    data = json.loads(content)

    def run_benchmark():
        if implementation == "copy_deepcopy":
            return copy.deepcopy(data)
        elif implementation == "json":
            return json.loads(json.dumps(data))
        elif implementation == "simplejson":
            return simplejson.loads(simplejson.dumps(data))
        elif implementation == "ujson":
            return ujson.loads(ujson.dumps(data))
        elif implementation == "orjson":
            return orjson.loads(orjson.dumps(data))
        else:
            raise ValueError("Invalid implementation: %s" % (implementation))

    result = benchmark(run_benchmark)
    assert result == data, "Output is not the same as the input"
