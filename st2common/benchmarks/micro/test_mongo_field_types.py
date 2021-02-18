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
This micro benchmark compares various approaches for saving large dictionaries in a MongoDB
collection using mongoengine layer.

StackStorm has a now long standing known issue where storing large executions can take a long time.

Two main reasons for that are:

    1. mongoengine adds a lot of overhead when converting large dicts to pymongo compatible format
    2. Our EscapedDictField perfoms escaping of . and $ character on every dict key recursively and
      that is slow for large nested dictionaries.

The biggest offender in our scenario is LiveActionDB.result field which contains actual execution
result which can be very large.

The good news is that even though we use Dict field for this value, for all purposes we treat this
value in the database as a binary blob aka we perform no search on this field value. This makes
things easier.

The goal of that benchmark is to determine a more efficient approach which is also not too hard to
implement in a backward compatible manner.
"""

import os
import json

import pytest
import ujson
import orjson

from st2common.service_setup import db_setup
from st2common.models.db import stormbase
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.liveaction import LiveAction
from st2common.fields import JSONDictField


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.abspath(os.path.join(BASE_DIR, "../fixtures/json"))

# 1. Current approach aka using EscapedDynamicField
class LiveActionDB_EscapedDynamicField(LiveActionDB):
    result = stormbase.EscapedDynamicField(default={})


# 2. Approach which uses new JSONDictField where value is stored as serialized JSON string / blob
class LiveActionDB_JSONField(LiveActionDB):
    result = JSONDictField(default={})



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
@pytest.mark.parametrize(
    "approach",
    [
        "escaped_dynamic_field",
        "json_dict_field",
    ],
    ids=[
        "escaped_dynamic_field",
        "json_dict_field",
    ],
)
@pytest.mark.benchmark(group="live_action_save")
def test_save_large_execution(benchmark, fixture_file: str, approach: str) -> None:
    with open(os.path.join(FIXTURES_DIR, fixture_file),"r") as fp:
        content = fp.read()

    data = json.loads(content)

    db_setup()

    def run_benchmark():
        if approach == "escaped_dynamic_field":
            model_cls = LiveActionDB_EscapedDynamicField
        elif approach == "json_dict_field":
            model_cls = LiveActionDB_JSONField
        else:
            raise ValueError("Invalid approach: %s" % (approach))

        live_action_db = model_cls()
        live_action_db.status = "succeeded"
        live_action_db.action = "core.local"
        live_action_db.result = data

        inserted_live_action_db = LiveAction.add_or_update(live_action_db)
        return inserted_live_action_db

    inserted_live_action_db = benchmark.pedantic(run_benchmark, iterations=3, rounds=3)
    retrieved_live_action_db = LiveAction.get_by_id(inserted_live_action_db.id)
    # Assert that result is correctly converted back to dict on retrieval
    assert inserted_live_action_db.result == data
    assert inserted_live_action_db == retrieved_live_action_db


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
@pytest.mark.parametrize(
    "approach",
    [
        "escaped_dynamic_field",
        "json_dict_field",
    ],
    ids=[
        "escaped_dynamic_field",
        "json_dict_field",
    ],
)
@pytest.mark.benchmark(group="live_action_read")
def test_read_large_execution(benchmark, fixture_file: str, approach: str) -> None:
    with open(os.path.join(FIXTURES_DIR, fixture_file),"r") as fp:
        content = fp.read()

    data = json.loads(content)

    db_setup()

    # 1. Insert the large execution
    if approach == "escaped_dynamic_field":
        model_cls = LiveActionDB_EscapedDynamicField
    elif approach == "json_dict_field":
        model_cls = LiveActionDB_JSONField
    else:
        raise ValueError("Invalid approach: %s" % (approach))

    live_action_db = model_cls()
    live_action_db.status = "succeeded"
    live_action_db.action = "core.local"
    live_action_db.result = data

    inserted_live_action_db = LiveAction.add_or_update(live_action_db)

    def run_benchmark():
        retrieved_live_action_db = LiveAction.get_by_id(inserted_live_action_db.id)
        return retrieved_live_action_db

    retrieved_live_action_db = benchmark.pedantic(run_benchmark, iterations=5, rounds=5)
    # Assert that result is correctly converted back to dict on retrieval
    assert retrieved_live_action_db == inserted_live_action_db
    assert retrieved_live_action_db.result == data
