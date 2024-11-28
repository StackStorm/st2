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

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

from kombu.serialization import pickle

import os
import json

import pytest
import zstandard as zstd

from st2common.models.db.liveaction import LiveActionDB
from st2common.transport import publishers
from st2common.transport.kombu import Exchange

from common import FIXTURES_DIR
from common import PYTEST_FIXTURE_FILE_PARAM_DECORATOR


@PYTEST_FIXTURE_FILE_PARAM_DECORATOR
@pytest.mark.parametrize(
    "algorithm",
    [
        "none",
        "zstandard",
    ],
    ids=[
        "none",
        "zstandard",
    ],
)
@pytest.mark.benchmark(group="no_publish")
def test_pickled_object_compression(
    benchmark, fixture_file: str, algorithm: str
) -> None:
    with open(os.path.join(FIXTURES_DIR, fixture_file), "r") as fp:
        content = fp.read()

    data = json.loads(content)

    def run_benchmark():
        live_action_db = LiveActionDB()
        live_action_db.status = "succeeded"
        live_action_db.action = "core.local"
        live_action_db.result = data

        serialized = pickle.dumps(live_action_db)

        if algorithm == "zstandard":
            c = zstd.ZstdCompressor()
            serialized = c.compress(serialized)

        return serialized

    result = benchmark.pedantic(run_benchmark, iterations=5, rounds=5)
    assert isinstance(result, bytes)


@PYTEST_FIXTURE_FILE_PARAM_DECORATOR
@pytest.mark.parametrize(
    "algorithm",
    [
        "none",
        "zstandard",
    ],
    ids=[
        "none",
        "zstandard",
    ],
)
@pytest.mark.benchmark(group="publish")
def test_pickled_object_compression_publish(
    benchmark, fixture_file: str, algorithm: str
) -> None:
    with open(os.path.join(FIXTURES_DIR, fixture_file), "r") as fp:
        content = fp.read()

    data = json.loads(content)

    publisher = publishers.PoolPublisher()

    exchange = Exchange("st2.execution.test", type="topic")

    if algorithm == "zstandard":
        compression = "zstd"
    else:
        compression = None

    def run_benchmark():
        live_action_db = LiveActionDB()
        live_action_db.status = "succeeded"
        live_action_db.action = "core.local"
        live_action_db.result = data

        publisher.publish(
            payload=live_action_db, exchange=exchange, compression=compression
        )

    benchmark.pedantic(run_benchmark, iterations=5, rounds=5)
