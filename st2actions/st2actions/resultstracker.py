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

import eventlet
from kombu import Connection
from kombu.mixins import ConsumerMixin
from oslo.config import cfg

from st2actions.query.base import QueryContext
from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.persistence.action import ActionExecutionState
from st2common.transport import actionexecutionstate, publishers
from st2common.util.greenpooldispatch import BufferedDispatcher

LOG = logging.getLogger(__name__)

ACTIONSTATE_WORK_Q = actionexecution.get_queue('st2.resultstracker.work',
                                               routing_key=publishers.CREATE_RK)


class ActionStateQueueConsumer(object):
    def __init__(self, connection, tracker):
        self.connection = connection
        self.container = RunnerContainer()
        self._dispatcher = BufferedDispatcher()
        self._tracker = tracker

    def shutdown(self):
        self._dispatcher.shutdown()

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(queues=[ACTIONSTATE_WORK_Q],
                            accept=['pickle'],
                            callbacks=[self.process_task])
        # use prefetch_count=1 for fair dispatch. This way workers that finish an item get the next
        # task and the work does not get queued behind any single large item.
        consumer.qos(prefetch_count=1)
        return [consumer]

    def process_task(self, body, message):
        # LOG.debug('process_task')
        # LOG.debug('     body: %s', body)
        # LOG.debug('     message.properties: %s', message.properties)
        # LOG.debug('     message.delivery_info: %s', message.delivery_info)
        try:
            self._dispatcher.dispatch(self._do_process_task, body)
        finally:
            message.ack()

    def _do_process_task(self, body):
        try:
            self.add_to_querier(body)
        except:
            LOG.exception('execute_action failed. Message body : %s', body)


class ResultsTracker(object):
    def __init__(self, q_connection=None):
        self._queue_consumer = ActionStateQueueConsumer(q_connection, self)
        self._consumer_thread = None
        self._queriers = {}
        self._failed_imports = set()

    def start(self):
        self._consumer_thread = eventlet.spawn(self._queue_consumer.run)

    def _bootstrap(self):
        all_states = ActionExecutionState.get_all()

        query_contexts_dict = {}
        for state in all_states:
            query_module_name = state['query_module']
            querier = self.get_querier(query_module_name)
            context = QueryContext(state.execution_id, state.query_context)
            query_contexts_dict[querier]

    def get_querier(self, query_module_name):
        if query_module_name not in self._queriers and query_module_name not in self._failed_imports:
            try:
                querier = self._import_query_module(query_module_name)
            except:
                LOG.exception('Failed importing query module: %s', query_module_name)
                self._failed_imports.add(query_module_name)
                continue
            else:
                self._queriers[query_module_name] = querier.get_instance()

        return self._queriers[query_module_name]

    def _import_query_module(self, module_name):
        return importlib.import_module(module_name, package=None)
def work():
