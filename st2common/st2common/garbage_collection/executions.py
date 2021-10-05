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
Module with utility functions for purging old action executions and
corresponding live action objects.
"""

from __future__ import absolute_import

import copy

import six
from mongoengine.errors import InvalidQueryError

from st2common.constants import action as action_constants
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.execution import ActionExecution
from st2common.persistence.execution import ActionExecutionOutput
from st2common.services import action as action_service
from st2common.services import workflows as workflow_service

__all__ = ["purge_executions", "purge_execution_output_objects"]

DONE_STATES = [
    action_constants.LIVEACTION_STATUS_SUCCEEDED,
    action_constants.LIVEACTION_STATUS_FAILED,
    action_constants.LIVEACTION_STATUS_TIMED_OUT,
    action_constants.LIVEACTION_STATUS_CANCELED,
]


def purge_executions(logger, timestamp, action_ref=None, purge_incomplete=False):
    """
    Purge action executions and corresponding live action, execution output objects.

    :param timestamp: Exections older than this timestamp will be deleted.
    :type timestamp: ``datetime.datetime

    :param action_ref: Only delete executions for the provided actions.
    :type action_ref: ``str``

    :param purge_incomplete: True to also delete executions which are not in a done state.
    :type purge_incomplete: ``bool``
    """
    if not timestamp:
        raise ValueError("Specify a valid timestamp to purge.")

    logger.info(
        "Purging executions older than timestamp: %s"
        % timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )

    filters = {}

    if purge_incomplete:
        filters["start_timestamp__lt"] = timestamp
    else:
        filters["end_timestamp__lt"] = timestamp
        filters["start_timestamp__lt"] = timestamp
        filters["status"] = {"$in": DONE_STATES}

    exec_filters = copy.copy(filters)
    if action_ref:
        exec_filters["action__ref"] = action_ref

    liveaction_filters = copy.deepcopy(filters)
    if action_ref:
        liveaction_filters["action"] = action_ref

    to_delete_execution_dbs = []

    # 1. Delete ActionExecutionDB objects
    try:
        # Note: We call list() on the query set object because it's lazyily evaluated otherwise
        to_delete_execution_dbs = list(
            ActionExecution.query(
                only_fields=["id"], no_dereference=True, **exec_filters
            )
        )
        deleted_count = ActionExecution.delete_by_query(**exec_filters)
    except InvalidQueryError as e:
        msg = (
            "Bad query (%s) used to delete execution instances: %s"
            "Please contact support."
            % (
                exec_filters,
                six.text_type(e),
            )
        )
        raise InvalidQueryError(msg)
    except:
        logger.exception(
            "Deletion of execution models failed for query with filters: %s.",
            exec_filters,
        )
    else:
        logger.info("Deleted %s action execution objects" % (deleted_count))

    # 2. Delete LiveActionDB objects
    try:
        deleted_count = LiveAction.delete_by_query(**liveaction_filters)
    except InvalidQueryError as e:
        msg = (
            "Bad query (%s) used to delete liveaction instances: %s"
            "Please contact support."
            % (
                liveaction_filters,
                six.text_type(e),
            )
        )
        raise InvalidQueryError(msg)
    except:
        logger.exception(
            "Deletion of liveaction models failed for query with filters: %s.",
            liveaction_filters,
        )
    else:
        logger.info("Deleted %s liveaction objects" % (deleted_count))

    # 3. Delete ActionExecutionOutputDB objects
    to_delete_exection_ids = [
        str(execution_db.id) for execution_db in to_delete_execution_dbs
    ]
    output_dbs_filters = {}
    output_dbs_filters["execution_id"] = {"$in": to_delete_exection_ids}

    try:
        deleted_count = ActionExecutionOutput.delete_by_query(**output_dbs_filters)
    except InvalidQueryError as e:
        msg = (
            "Bad query (%s) used to delete execution output instances: %s"
            "Please contact support." % (output_dbs_filters, six.text_type(e))
        )
        raise InvalidQueryError(msg)
    except:
        logger.exception(
            "Deletion of execution output models failed for query with filters: %s.",
            output_dbs_filters,
        )
    else:
        logger.info("Deleted %s execution output objects" % (deleted_count))

    zombie_execution_instances = len(
        ActionExecution.query(only_fields=["id"], no_dereference=True, **exec_filters)
    )
    zombie_liveaction_instances = len(
        LiveAction.query(only_fields=["id"], no_dereference=True, **liveaction_filters)
    )

    if (zombie_execution_instances > 0) or (zombie_liveaction_instances > 0):
        logger.error("Zombie execution instances left: %d.", zombie_execution_instances)
        logger.error(
            "Zombie liveaction instances left: %s.", zombie_liveaction_instances
        )

    # Print stats
    logger.info("All execution models older than timestamp %s were deleted.", timestamp)


def purge_execution_output_objects(logger, timestamp, action_ref=None):
    """
    Purge action executions output objects.

    :param timestamp: Objects older than this timestamp will be deleted.
    :type timestamp: ``datetime.datetime

    :param action_ref: Only delete objects for the provided actions.
    :type action_ref: ``str``
    """
    if not timestamp:
        raise ValueError("Specify a valid timestamp to purge.")

    logger.info(
        "Purging action execution output objects older than timestamp: %s"
        % timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    )

    filters = {}
    filters["timestamp__lt"] = timestamp

    if action_ref:
        filters["action_ref"] = action_ref

    try:
        deleted_count = ActionExecutionOutput.delete_by_query(**filters)
    except InvalidQueryError as e:
        msg = (
            "Bad query (%s) used to delete execution output instances: %s"
            "Please contact support." % (filters, six.text_type(e))
        )
        raise InvalidQueryError(msg)
    except:
        logger.exception(
            "Deletion of execution output models failed for query with filters: %s.",
            filters,
        )
    else:
        logger.info("Deleted %s execution output objects" % (deleted_count))


def purge_orphaned_workflow_executions(logger):
    """
    Purge workflow executions that are idled and identified as orphans.
    """
    # Cancel workflow executions that are identified as orphans. The workflow executions are
    # marked as canceled instead of failed because error handling during normal operation
    # failed and the system does not know what state the workflow execution is in. A failed
    # workflow execution can be rerun from failed task(s). Since we do not know what state
    # the workflow execution is in because correct data may not be recorded in the database
    # as a result of the original failure, the garbage collection routine here cancels
    # the workflow execution so it cannot be rerun from failed task(s).
    for ac_ex_db in workflow_service.identify_orphaned_workflows():
        lv_ac_db = LiveAction.get(id=ac_ex_db.liveaction["id"])
        action_service.request_cancellation(lv_ac_db, None)
