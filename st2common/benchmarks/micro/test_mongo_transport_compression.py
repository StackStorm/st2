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

from common import FIXTURES_DIR
from common import PYTEST_FIXTURE_FILE_PARAM_DECORATOR


@PYTEST_FIXTURE_FILE_PARAM_DECORATOR
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
def test_save_execution(benchmark, fixture_file: str, compression):
    with open(os.path.join(FIXTURES_DIR, fixture_file), "rb") as fp:
        content = fp.read()

    cfg.CONF.set_override(name="compressors", group="database", override=compression)

    # NOTE: It's important we correctly reestablish connection before each setting change
    disconnect()
    connection = db_setup()

    if compression is None:
        assert "compressors" not in str(connection)
    elif compression == "zstd":
        assert "compressors=['zstd']" in str(connection)

    def run_benchmark():
        live_action_db = LiveActionDB()
        live_action_db.status = "succeeded"
        live_action_db.action = "core.local"
        live_action_db.result = content

        inserted_live_action_db = LiveAction.add_or_update(live_action_db)
        return inserted_live_action_db

    inserted_live_action_db = benchmark(run_benchmark)
    assert inserted_live_action_db.result == content


@PYTEST_FIXTURE_FILE_PARAM_DECORATOR
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
def test_read_execution(benchmark, fixture_file: str, compression):
    with open(os.path.join(FIXTURES_DIR, fixture_file), "rb") as fp:
        content = fp.read()

    cfg.CONF.set_override(name="compressors", group="database", override=compression)

    # NOTE: It's important we correctly reestablish connection before each setting change
    disconnect()
    connection = db_setup()

    if compression is None:
        assert "compressors" not in str(connection)
    elif compression == "zstd":
        assert "compressors=['zstd']" in str(connection)

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
