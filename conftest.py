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


def get_group(items, group_count, group_id):
    """Get the items from the passed in group based on group count."""
    if not (1 <= group_id <= group_count):
        raise ValueError("Invalid test-group argument")

    start = group_id - 1
    return items[start:len(items):group_count]


def pytest_addoption(parser):
    group = parser.getgroup('split your tests into evenly sized groups and run them')
    group.addoption('--test-group-count', dest='test-group-count', type=int,
                    help='The number of groups to split the tests into')
    group.addoption('--test-group', dest='test-group', type=int,
                    help='The group of tests that should be executed')


def pytest_collection_modifyitems(session, config, items):
    group_count = config.getoption('test-group-count')
    group_id = config.getoption('test-group')

    if not group_count or not group_id:
        return

    items[:] = get_group(items, group_count, group_id)

    terminal_reporter = config.pluginmanager.get_plugin('terminalreporter')
    terminal_writer = create_terminal_writer(config)
    message = terminal_writer.markup(
        'Running test group #{0} ({1} tests)\n'.format(
            group_id,
            len(items)
        ),
        yellow=True
    )
    terminal_reporter.write(message)
