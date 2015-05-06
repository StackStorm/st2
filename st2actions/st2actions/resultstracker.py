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

from collections import defaultdict

import eventlet
import importlib
from kombu import Connection
from kombu.mixins import ConsumerMixin
from oslo.config import cfg
import six

from st2actions.query.base import QueryContext
from st2common import log as logging
from st2common.persistence.action import ActionExecutionState
from st2common.transport import actionexecutionstate, publishers
from st2common.util.greenpooldispatch import BufferedDispatcher

LOG = logging.getLogger(__name__)

ACTIONSTATE_WORK_Q = actionexecutionstate.get_queue('st2.resultstracker.work',
                                                    routing_key=publishers.CREATE_RK)


class ActionStateQueueConsumer(ConsumerMixin):
    def __init__(self, connection, tracker):
        self.connection = connection
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
        LOG.debug('process_task')
        LOG.debug('     body: %s', body)
        LOG.debug('     message.properties: %s', message.properties)
        LOG.debug('     message.delivery_info: %s', message.delivery_info)
        try:
            self._dispatcher.dispatch(self._do_process_task, body)
        finally:
            message.ack()

    def _do_process_task(self, body):
        try:
            self._add_to_querier(body)
        except:
            LOG.exception('Add query_context failed. Message body : %s', body)

    def _add_to_querier(self, body):
        querier = self._tracker.get_querier(body.query_module)
        context = QueryContext.from_model(body)
        querier.add_queries(query_contexts=[context])
        return


class ResultsTracker(object):
    def __init__(self, q_connection=None):
        self._queue_consumer = ActionStateQueueConsumer(q_connection, self)
        self._consumer_thread = None
        self._queriers = {}
        self._query_threads = []
        self._failed_imports = set()

    def start(self):
        self._bootstrap()
        self._consumer_thread = eventlet.spawn(self._queue_consumer.run)
        self._consumer_thread.wait()
        for thread in self._query_threads:
            thread.wait()

    def shutdown(self):
        LOG.info('Tracker shutting down. Stats from queriers:')
        self._print_stats()
        self._queue_consumer.shutdown()

    def _print_stats(self):
        for name, querier in six.iteritems(self._queriers):
            if querier:
                querier.print_stats()

    def _bootstrap(self):
        all_states = ActionExecutionState.get_all()
        LOG.info('Found %d pending states in db.' % len(all_states))

        query_contexts_dict = defaultdict(list)
        for state_db in all_states:
            try:
                context = QueryContext.from_model(state_db)
            except:
                LOG.exception('Invalid state object: %s', state_db)
                continue
            query_module_name = state_db.query_module
            querier = self.get_querier(query_module_name)

            if querier is not None:
                query_contexts_dict[querier].append(context)

        for querier, contexts in six.iteritems(query_contexts_dict):
            LOG.info('Found %d pending actions for query module %s', len(contexts), querier)
            querier.add_queries(query_contexts=contexts)

    def get_querier(self, query_module_name):
        if (query_module_name not in self._queriers and
                query_module_name not in self._failed_imports):
            try:
                query_module = self._import_query_module(query_module_name)
            except:
                LOG.exception('Failed importing query module: %s', query_module_name)
                self._failed_imports.add(query_module_name)
                self._queriers[query_module_name] = None
            else:
                querier = query_module.get_instance()
                self._queriers[query_module_name] = querier
                self._query_threads.append(eventlet.spawn(querier.start))

        return self._queriers[query_module_name]

    def _import_query_module(self, module_name):
        return importlib.import_module(module_name, package=None)


def get_tracker():
    with Connection(cfg.CONF.messaging.url) as conn:
        tracker = ResultsTracker(q_connection=conn)
        return tracker
