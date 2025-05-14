# Copyright 2022 The StackStorm Authors.
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
import hashlib
from typing import Iterable, List, Sequence

from _pytest import nodes
from _pytest.config import create_terminal_writer


def pytest_configure(config):
    import sys

    sys._called_from_test = True


def pytest_unconfigure(config):
    import sys

    del sys._called_from_test


# TODO: Remove everything below here when we get rid of the Makefile
# everything below this is based on (MIT licensed) by mark-adams:
# https://github.com/mark-adams/pytest-test-groups/blob/5eca437ef95d23e8674b9e8765ce16005159d334/pytest_test_groups/__init__.py
# with some inspiration from (MIT licensed) by Adam Gleave:
# https://github.com/AdamGleave/pytest-shard/blob/64610a08dac6b0511b6d51cf895d0e1040d162ad/pytest_shard/pytest_shard.py


def get_group(
    items: Iterable[nodes.Node], group_count: int, group_id: int
) -> Sequence[nodes.Node]:
    """Get the items from the passed in group based on group count."""
    if not (0 <= group_id < group_count):
        raise ValueError("Invalid test-group argument")

    def get_group_id(node: nodes.Node) -> int:
        # use the file path instead of node id, so all tests in a file run together.
        path_bytes = str(node.path).encode()
        digest_bytes = hashlib.sha256(path_bytes).digest()
        digest = int.from_bytes(digest_bytes, "little")
        return digest % group_count

    return [item for item in items if get_group_id(item) == group_id]


def pytest_addoption(parser):
    group = parser.getgroup("split your tests into evenly sized groups and run them")
    group.addoption(
        "--test-group-count",
        dest="test-group-count",
        type=int,
        default=-1,
        help="The number of groups to split the tests into",
    )
    group.addoption(
        "--test-group",
        dest="test-group",
        type=int,
        default=-1,
        help="The group of tests that should be executed",
    )


def pytest_collection_modifyitems(session, config, items: List[nodes.Node]):
    group_count = config.getoption("test-group-count")
    group_id = config.getoption("test-group")

    if group_count < 1 or group_id < 0:
        return

    items[:] = get_group(items, group_count, group_id)

    terminal_reporter = config.pluginmanager.get_plugin("terminalreporter")
    terminal_writer = create_terminal_writer(config)
    message = terminal_writer.markup(
        "Running test group #{0} ({1} tests)\n".format(group_id, len(items)),
        yellow=True,
    )
    terminal_reporter.write(message)
