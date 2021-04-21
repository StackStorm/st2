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
Benchmarks which measure how much overhead enabling transport / network level MongoDB compression
adds.
"""

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import os

import pytest

from oslo_config import cfg
from mongoengine.connection import disconnect

from st2common.service_setup import db_setup
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.liveaction import LiveAction

from test_mongo_field_types import FIXTURES_DIR


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
        "tiny_1",
        "json_61kb",
        "json_647kb",
        "json_4mb",
        "json_8mb",
        "json_4mb_single_large_field",
    ],
)
@pytest.mark.parametrize(
    "compression",
    [
        None,
        "zstd",
    ],
    ids=[
        "none",
        "zstd",
    ],
)
@pytest.mark.benchmark(group="test_model_save")
def test_save_exection(benchmark, fixture_file: str, compression):
    with open(os.path.join(FIXTURES_DIR, fixture_file), "rb") as fp:
        content = fp.read()

    cfg.CONF.set_override(name="compressors", group="database", override=compression)

    # NOTE: It's important we correctly reestablish connection before each setting change
    disconnect()
    db_setup()

    def run_benchmark():
        live_action_db = LiveActionDB()
        live_action_db.status = "succeeded"
        live_action_db.action = "core.local"
        live_action_db.result = content

        inserted_live_action_db = LiveAction.add_or_update(live_action_db)
        return inserted_live_action_db

    inserted_live_action_db = benchmark(run_benchmark)
    assert inserted_live_action_db.result == content


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
        "tiny_1",
        "json_61kb",
        "json_647kb",
        "json_4mb",
        "json_8mb",
        "json_4mb_single_large_field",
    ],
)
@pytest.mark.parametrize(
    "compression",
    [
        None,
        "zstd",
    ],
    ids=[
        "none",
        "zstd",
    ],
)
@pytest.mark.benchmark(group="test_model_read")
def test_read_exection(benchmark, fixture_file: str, compression):
    with open(os.path.join(FIXTURES_DIR, fixture_file), "rb") as fp:
        content = fp.read()

    cfg.CONF.set_override(name="compressors", group="database", override=compression)

    # NOTE: It's important we correctly reestablish connection before each setting change
    disconnect()
    db_setup()

    live_action_db = LiveActionDB()
    live_action_db.status = "succeeded"
    live_action_db.action = "core.local"
    live_action_db.result = content

    inserted_live_action_db = LiveAction.add_or_update(live_action_db)

    def run_benchmark():
        retrieved_live_action_db = LiveAction.get_by_id(inserted_live_action_db.id)
        return retrieved_live_action_db

    retrieved_live_action_db = benchmark(run_benchmark)
    # Assert that result is correctly converted back to dict on retrieval
    assert retrieved_live_action_db == inserted_live_action_db
