# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import abc
import eventlet
import six.moves.queue
import six
import time

from oslo_config import cfg

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.exceptions import db as db_exc
from st2common.persistence.executionstate import ActionExecutionState
from st2common.persistence.liveaction import LiveAction
from st2common.runners import utils as runners_utils
from st2common.services import executions
from st2common.util import date as date_utils

LOG = logging.getLogger(__name__)

__all__ = [
    'Querier',
    'QueryContext'
]


@six.add_metaclass(abc.ABCMeta)
class Querier(object):
    delete_state_object_on_error = True

    def _get_config_value(self, config_option):
        config_value = None

        if 'results_tracker' in cfg.CONF and config_option in cfg.CONF.results_tracker:
            config_value = getattr(cfg.CONF.results_tracker, config_option)
            LOG.warning('You are using deprecated config group "results_tracker" for "%s". '
                        'Please use "resultstracker" group instead.', config_option)

        if not config_value and config_option in cfg.CONF.resultstracker:
            config_value = getattr(cfg.CONF.resultstracker, config_option)

        return config_value

    def __init__(self):
        self._empty_q_sleep_time = self._get_config_value('empty_q_sleep_time')
        self._no_workers_sleep_time = self._get_config_value('no_workers_sleep_time')
        self._query_interval = self._get_config_value('query_interval')
        self._query_thread_pool_size = self._get_config_value('thread_pool_size')
        self._query_contexts = six.moves.queue.Queue()
        self._thread_pool = eventlet.GreenPool(self._query_thread_pool_size)
        self._started = False

    def start(self):
        self._started = True
        while True:
            while self._query_contexts.empty():
                eventlet.greenthread.sleep(self._empty_q_sleep_time)
            while self._thread_pool.free() <= 0:
                eventlet.greenthread.sleep(self._no_workers_sleep_time)
            self._fire_queries()
            eventlet.sleep(self._query_interval)

    def add_queries(self, query_contexts=None):
        if query_contexts is None:
            query_contexts = []
        LOG.debug('Adding queries to querier: %s' % query_contexts)
        for query_context in query_contexts:
            self._query_contexts.put((time.time(), query_context))

    def is_started(self):
        return self._started

    def _fire_queries(self, blocking=False):
        if self._thread_pool.free() <= 0:
            return

        now = time.time()
        reschedule_queries = []

        while not self._query_contexts.empty() and self._thread_pool.free() > 0:
            (last_query_time, query_context) = self._query_contexts.get_nowait()
            if now - last_query_time < self._query_interval:
                reschedule_queries.append((last_query_time, query_context))
                continue
            else:
                if not blocking:
                    self._thread_pool.spawn(
                        self._query_and_save_results,
                        query_context,
                        last_query_time
                    )
                # Add an option to block and execute the function directly for unit tests.
                else:
                    self._query_and_save_results(
                        query_context,
                        last_query_time
                    )

        for query in reschedule_queries:
            self._query_contexts.put((query[0], query[1]))

    def _query_and_save_results(self, query_context, last_query_time=None):
        this_query_time = time.time()
        execution_id = query_context.execution_id
        actual_query_context = query_context.query_context

        LOG.debug('Querying external service for results. Context: %s' % actual_query_context)
        try:
            (status, results) = self.query(
                execution_id,
                actual_query_context,
                last_query_time=last_query_time
            )
        except:
            LOG.exception('Failed querying results for liveaction_id %s.', execution_id)
            if self.delete_state_object_on_error:
                self._delete_state_object(query_context)
                LOG.debug('Removed state object %s.', query_context)
            return

        liveaction_db = None
        try:
            liveaction_db = self._update_action_results(execution_id, status, results)
        except Exception:
            LOG.exception('Failed updating action results for liveaction_id %s', execution_id)
            if self.delete_state_object_on_error:
                self._delete_state_object(query_context)
                LOG.debug('Removed state object %s.', query_context)
            return

        if (status in action_constants.LIVEACTION_COMPLETED_STATES or
                status == action_constants.LIVEACTION_STATUS_PAUSED):
            runners_utils.invoke_post_run(liveaction_db)
            self._delete_state_object(query_context)
            LOG.debug(
                "Detailed workflow liveaction results - ", extra={'liveaction_db': liveaction_db}
            )
            return

        if not self._is_state_object_exist(query_context):
            LOG.warning(
                'Query for liveaction_id %s is not rescheduled '
                'because state object %s has been deleted.',
                execution_id,
                query_context.id
            )

            return

        self._query_contexts.put((this_query_time, query_context))

    def _update_action_results(self, execution_id, status, results):
        liveaction_db = LiveAction.get_by_id(execution_id)
        if not liveaction_db:
            raise Exception('No DB model for liveaction_id: %s' % execution_id)

        if liveaction_db.status != action_constants.LIVEACTION_STATUS_CANCELED:
            liveaction_db.status = status

        liveaction_db.result = results

        # Action has completed, record end_timestamp
        if (liveaction_db.status in action_constants.LIVEACTION_COMPLETED_STATES and
                not liveaction_db.end_timestamp):
            liveaction_db.end_timestamp = date_utils.get_datetime_utc_now()

        # update liveaction, update actionexecution and then publish update.
        updated_liveaction = LiveAction.add_or_update(liveaction_db, publish=False)
        executions.update_execution(updated_liveaction)
        LiveAction.publish_update(updated_liveaction)

        return updated_liveaction

    def _delete_state_object(self, query_context):
        state_db = None

        try:
            state_db = ActionExecutionState.get_by_id(query_context.id)
        except db_exc.StackStormDBObjectNotFoundError:
            pass

        if state_db is not None:
            try:
                LOG.info('Clearing state object: %s', state_db)
                ActionExecutionState.delete(state_db)
            except:
                LOG.exception('Failed clearing state object: %s', state_db)

    def _is_state_object_exist(self, query_context):
        state_db = None

        try:
            state_db = ActionExecutionState.get_by_id(query_context.id)
        except db_exc.StackStormDBObjectNotFoundError:
            pass

        return (state_db is not None)

    def query(self, execution_id, query_context, last_query_time=None):
        """
        This is the method individual queriers must implement.
        This method should return a tuple of (status, results).

        status should be one of LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_RUNNING,
        LIVEACTION_STATUS_FAILED defined in st2common.constants.action.
        """
        pass

    def print_stats(self):
        LOG.info('\t --- Name: %s, pending queuries: %d', self.__class__.__name__,
                 self._query_contexts.qsize())


class QueryContext(object):
    def __init__(self, obj_id, execution_id, query_context, query_module):
        self.id = obj_id
        self.execution_id = execution_id
        self.query_context = query_context
        self.query_module = query_module

    @classmethod
    def from_model(cls, model):
        return QueryContext(str(model.id), str(model.execution_id), model.query_context,
                            model.query_module)

    def __repr__(self):
        return ('<QueryContext id=%s,execution_id=%s,query_context=%s>' %
                (self.id, self.execution_id, self.query_context))
