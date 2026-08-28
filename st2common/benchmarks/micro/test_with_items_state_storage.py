# Copyright 2025 The StackStorm Authors.
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
This micro benchmark compares two approaches for persisting individual item states of an
itemized ("with items") task execution.

Historically all item states were stored inline on ``TaskExecutionDB.result["items"]`` as a
single list. Every time a single item completed, the *entire* task execution document (with
the whole ``items`` list) had to be read, mutated and written back. As the number of items
grows this becomes O(N) work per item update and O(N^2) work for the whole task, and the
per-write payload keeps growing with the item count.

The new approach stores each item state in its own small ``TaskItemStateDB`` record, so a
single item update only reads and writes one small document regardless of how many items the
task has (O(1) per item update, O(N) for the whole task).

This benchmark simulates processing every item of an itemized task once and measures the total
time for both approaches at a few different item counts so the improvement can be quantified.
"""

from st2common.util.monkey_patch import monkey_patch

monkey_patch()

import pytest

from st2common.service_setup import db_setup
from st2common.constants import action as ac_const
from st2common.models.db.workflow import TaskExecutionDB
from st2common.models.db.workflow import TaskItemStateDB
from st2common.persistence.workflow import TaskExecution
from st2common.persistence.workflow import TaskItemState


# A representative per-item result payload (e.g. the stdout/stderr of an action). Action
# results are frequently non-trivial in size; we use a ~2 KB stdout here. This matters
# because the inline approach re-serializes and rewrites the whole ``items`` list (every
# item's result) on every single item update, whereas the per-record approach only ever
# writes one item's result at a time.
ITEM_RESULT = {
    "failed": False,
    "succeeded": True,
    "return_code": 0,
    "stdout": "item processed successfully. " * 64,
    "stderr": "",
}

ITEM_COUNTS = [10, 100, 500]


def _create_task_execution():
    task_ex_db = TaskExecutionDB(
        workflow_execution="000000000000000000000000",
        task_name="task1",
        task_id="task1",
        task_route=0,
        status=ac_const.LIVEACTION_STATUS_RUNNING,
        itemized=True,
    )
    return task_ex_db


def _setup_inline_result(items_count):
    """Old approach: pre-allocate the inline ``items`` list on the task execution."""
    task_ex_db = _create_task_execution()
    task_ex_db.items_count = items_count
    task_ex_db.result = {"items": [None] * items_count}
    task_ex_db = TaskExecution.add_or_update(task_ex_db, publish=False)
    return str(task_ex_db.id)


def _setup_item_state_records(items_count):
    """New approach: one small TaskItemStateDB record per item."""
    task_ex_db = _create_task_execution()
    task_ex_db.items_count = items_count
    task_ex_db.result = {"items_count": items_count}
    task_ex_db = TaskExecution.add_or_update(task_ex_db, publish=False)
    task_ex_id = str(task_ex_db.id)

    for item_id in range(items_count):
        item_state_db = TaskItemStateDB(
            task_execution=task_ex_id,
            item_id=item_id,
            status=ac_const.LIVEACTION_STATUS_REQUESTED,
            context={},
        )
        TaskItemState.insert(item_state_db, publish=False)

    return task_ex_id


def _update_inline_result(task_ex_id, items_count):
    """Record every item state the old way: reload + rewrite the whole task document."""
    for item_id in range(items_count):
        task_ex_db = TaskExecution.get_by_id(task_ex_id)
        task_ex_db.result["items"][item_id] = {
            "status": ac_const.LIVEACTION_STATUS_SUCCEEDED,
            "result": ITEM_RESULT,
        }
        TaskExecution.add_or_update(task_ex_db, publish=False)


def _update_item_state_records(task_ex_id, items_count):
    """Record every item state the new way: reload + rewrite a single small record."""
    for item_id in range(items_count):
        item_state_db = TaskItemState.get_by_task_and_item(task_ex_id, item_id)
        item_state_db.status = ac_const.LIVEACTION_STATUS_SUCCEEDED
        item_state_db.result = ITEM_RESULT
        TaskItemState.add_or_update(item_state_db, publish=False)


@pytest.mark.parametrize("items_count", ITEM_COUNTS, ids=[str(c) for c in ITEM_COUNTS])
@pytest.mark.parametrize(
    "approach",
    ["inline_result", "item_state_records"],
    ids=["inline_result", "item_state_records"],
)
@pytest.mark.benchmark(group="with_items_state_storage")
def test_record_all_item_states(benchmark, approach: str, items_count: int) -> None:
    db_setup()

    if approach == "inline_result":
        setup_fn = _setup_inline_result
        update_fn = _update_inline_result
    elif approach == "item_state_records":
        setup_fn = _setup_item_state_records
        update_fn = _update_item_state_records
    else:
        raise ValueError("Invalid approach: %s" % (approach,))

    # The task execution / item state records are created once, outside the timed section.
    # This is a one-time cost per task; the benchmark focuses on the repeated per-item state
    # update, which is the hot path that runs once per item (and, in production, concurrently
    # across items). Recording an item state the old way reads and rewrites the entire task
    # execution document (the whole growing ``items`` list); the new way reads and rewrites a
    # single small record.
    task_ex_id = setup_fn(items_count)

    def run_benchmark():
        update_fn(task_ex_id, items_count)
        return task_ex_id

    # Use pedantic mode with a bounded number of rounds: each round performs items_count
    # database reads and writes, so the default auto-calibrated benchmark would be
    # prohibitively slow for the larger item counts.
    benchmark.pedantic(run_benchmark, rounds=3, iterations=1, warmup_rounds=0)

    # Sanity check that all item states were recorded.
    if approach == "inline_result":
        task_ex_db = TaskExecution.get_by_id(task_ex_id)
        recorded = task_ex_db.result["items"]
        assert len(recorded) == items_count
        assert all(item is not None for item in recorded)
    else:
        item_state_dbs = TaskItemState.query_by_task_execution(task_ex_id)
        assert len(item_state_dbs) == items_count
        assert all(
            isd.status == ac_const.LIVEACTION_STATUS_SUCCEEDED for isd in item_state_dbs
        )
