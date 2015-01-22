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

import abc
import eventlet
import Queue
import six
import time

from st2actions.container.service import RunnerContainerService
from st2actions.runners import get_runner
from st2common import log as logging
from st2common.constants.action import (ACTIONEXEC_STATUS_FAILED,
                                        ACTIONEXEC_STATUS_SUCCEEDED)
from st2common.persistence.action import (ActionExecution, ActionExecutionState)
from st2common.util.action_db import (get_action_by_ref, get_runnertype_by_name)


LOG = logging.getLogger(__name__)
DONE_STATES = [ACTIONEXEC_STATUS_FAILED, ACTIONEXEC_STATUS_SUCCEEDED]


@six.add_metaclass(abc.ABCMeta)
class Querier(object):
    def __init__(self, threads_pool_size=10, query_interval=1, empty_q_sleep_time=5,
                 no_workers_sleep_time=1, container_service=None):
        self._query_threads_pool_size = threads_pool_size
        self._query_contexts = Queue.Queue()
        self._thread_pool = eventlet.GreenPool(self._query_threads_pool_size)
        self._empty_q_sleep_time = empty_q_sleep_time
        self._no_workers_sleep_time = no_workers_sleep_time
        self._query_interval = query_interval
        if not container_service:
            container_service = RunnerContainerService()
        self.container_service = container_service
        self._started = False

    def start(self):
        self._started = True
        while True:
            while self._query_contexts.empty():
                eventlet.greenthread.sleep(self._empty_q_sleep_time)
            while self._thread_pool.free() <= 0:
                eventlet.greenthread.sleep(self._no_workers_sleep_time)
            self._fire_queries()

    def add_queries(self, query_contexts=[]):
        LOG.debug('Adding queries to querier: %s' % query_contexts)
        for query_context in query_contexts:
            self._query_contexts.put((time.time(), query_context))

    def is_started(self):
        return self._started

    def _fire_queries(self):
        if self._thread_pool.free() <= 0:
            return
        while not self._query_contexts.empty() and self._thread_pool.free() > 0:
            (last_query_time, query_context) = self._query_contexts.get_nowait()
            if time.time() - last_query_time < self._query_interval:
                self._query_contexts.put((last_query_time, query_context))
                continue
            else:
                self._thread_pool.spawn(self._query_and_save_results, query_context)

    def _query_and_save_results(self, query_context):
        execution_id = query_context.execution_id
        actual_query_context = query_context.query_context

        LOG.debug('Querying external service for results. Context: %s' % actual_query_context)
        try:
            (status, results) = self.query(execution_id, actual_query_context)
        except:
            LOG.exception('Failed querying results for action_execution_id %s.', execution_id)
            self._delete_state_object(query_context)
            return

        done = (status in DONE_STATES)

        actionexec_db = ActionExecution.get_by_id(execution_id)
        if not actionexec_db:
            LOG.exception('Action execution %s no longer exists.' % execution_id)
            self._delete_state_object(query_context)
            return

        actionexec_db = self._update_action_results(actionexec_db, status, results)

        if done:
            action_db = get_action_by_ref(actionexec_db.action)
            if not action_db:
                LOG.exception('Unable to invoke post run. Action %s '
                              'no longer exists.' % actionexec_db.action)
                self._delete_state_object(query_context)
                return
            self._invoke_post_run(actionexec_db, action_db)
            self._delete_state_object(query_context)
            return

        self._query_contexts.put((time.time(), query_context))

    def _update_action_results(self, actionexec_db, status, results):
        actionexec_db.result = results
        actionexec_db.status = status
        updated_exec = ActionExecution.add_or_update(actionexec_db)
        return updated_exec

    def _invoke_post_run(self, actionexec_db, action_db):
        LOG.info('Invoking post run for action execution %s. Action=%s; Runner=%s',
                 actionexec_db.id, action_db.name, action_db.runner_type['name'])

        # Get an instance of the action runner.
        runnertype_db = get_runnertype_by_name(action_db.runner_type['name'])
        runner = get_runner(runnertype_db.runner_module)

        # Configure the action runner.
        runner.container_service = RunnerContainerService()
        runner.action = action_db
        runner.action_name = action_db.name
        runner.action_execution_id = str(actionexec_db.id)
        runner.entry_point = RunnerContainerService.get_entry_point_abs_path(
            pack=action_db.pack, entry_point=action_db.entry_point)
        runner.context = getattr(actionexec_db, 'context', dict())
        runner.callback = getattr(actionexec_db, 'callback', dict())
        runner.libs_dir_path = RunnerContainerService.get_action_libs_abs_path(
            pack=action_db.pack, entry_point=action_db.entry_point)

        # Invoke the post_run method.
        runner.post_run(actionexec_db.status, actionexec_db.result)

    def _delete_state_object(self, query_context):
        state_db = ActionExecutionState.get_by_id(query_context.id)
        if state_db is not None:
            try:
                ActionExecutionState.delete(state_db)
            except:
                LOG.exception('Failed clearing state object: %s', state_db)

    def query(self, execution_id, query_context):
        """
        This is the method individual queriers must implement.
        This method should return a tuple of (status, results).

        status should be one of ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_RUNNING,
        ACTIONEXEC_STATUS_FAILED defined in st2common.constants.action.
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
