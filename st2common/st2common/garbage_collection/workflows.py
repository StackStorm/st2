# Copyright 2020 Extreme Networks, Inc.
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
Module with utility functions for purging old action workflows.
"""
from __future__ import absolute_import

import copy

import six
from mongoengine.errors import InvalidQueryError

from st2common.constants import action as action_constants
from st2common.persistence.workflow import WorkflowExecution
from st2common.persistence.workflow import TaskExecution


__all__ = [
    'purge_workflow_execution',
    'purge_task_execution'
]

#TODO: Are these valid too..
DONE_STATES = [action_constants.LIVEACTION_STATUS_SUCCEEDED,
               action_constants.LIVEACTION_STATUS_FAILED,
               action_constants.LIVEACTION_STATUS_TIMED_OUT,
               action_constants.LIVEACTION_STATUS_CANCELED]


def purge_workflow_execution(logger, timestamp, action_ref=None, purge_incomplete=False):
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
        raise ValueError('Specify a valid timestamp to purge.')

    logger.info('Purging executions older than timestamp: %s' %
                timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

    filters = {}

    if purge_incomplete:
        filters['start_timestamp__lt'] = timestamp
    else:
        filters['end_timestamp__lt'] = timestamp
        filters['start_timestamp__lt'] = timestamp
        filters['status'] = {'$in': DONE_STATES}

    exec_filters = copy.copy(filters)
    # TODO: Are these parameters valid.
    # if action_ref:
    #     exec_filters['action__ref'] = action_ref
    #
    # liveaction_filters = copy.deepcopy(filters)
    # if action_ref:
    #     liveaction_filters['action'] = action_ref

    # 1. Delete ActionExecutionDB objects
    try:
        # Note: We call list() on the query set object because it's lazyily evaluated otherwise
        # to_delete_execution_dbs = list(WorkflowExecution.query(only_fields=['id'],
        #                                                      no_dereference=True,
        #                                                      **exec_filters))
        deleted_count = WorkflowExecution.delete_by_query(**exec_filters)
    except InvalidQueryError as e:
        msg = ('Bad query (%s) used to delete execution instances: %s'
               'Please contact support.' % (exec_filters, six.text_type(e)))
        raise InvalidQueryError(msg)
    except:
        logger.exception('Deletion of execution models failed for query with filters: %s.',
                         exec_filters)
    else:
        logger.info('Deleted %s action execution objects' % deleted_count)

    zombie_execution_instances = len(WorkflowExecution.query(only_fields=['id'],
                                                             no_dereference=True,
                                                             **exec_filters))

    if zombie_execution_instances > 0:
        logger.error('Zombie execution instances left: %d.', zombie_execution_instances)

    # Print stats
    logger.info('All execution models older than timestamp %s were deleted.', timestamp)


def purge_task_execution(logger, timestamp, action_ref=None, purge_incomplete=False):
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
        raise ValueError('Specify a valid timestamp to purge.')

    logger.info('Purging executions older than timestamp: %s' %
                timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))

    filters = {}

    if purge_incomplete:
        filters['start_timestamp__lt'] = timestamp
    else:
        filters['end_timestamp__lt'] = timestamp
        filters['start_timestamp__lt'] = timestamp
        filters['status'] = {'$in': DONE_STATES}

    exec_filters = copy.copy(filters)
    try:
        # Note: We call list() on the query set object because it's lazyily evaluated otherwise
        # to_delete_execution_dbs = list(WorkflowExecution.query(only_fields=['id'],
        #                                                      no_dereference=True,
        #                                                      **exec_filters))
        deleted_count = TaskExecution.delete_by_query(**exec_filters)
    except InvalidQueryError as e:
        msg = ('Bad query (%s) used to delete execution instances: %s'
               'Please contact support.' % (exec_filters, six.text_type(e)))
        raise InvalidQueryError(msg)
    except:
        logger.exception('Deletion of execution models failed for query with filters: %s.',
                         exec_filters)
    else:
        logger.info('Deleted %s action execution objects' % deleted_count)

    zombie_execution_instances = len(WorkflowExecution.query(only_fields=['id'],
                                                             no_dereference=True,
                                                             **exec_filters))

    if zombie_execution_instances > 0:
        logger.error('Zombie execution instances left: %d.', zombie_execution_instances)

    # Print stats
    logger.info('All execution models older than timestamp %s were deleted.', timestamp)