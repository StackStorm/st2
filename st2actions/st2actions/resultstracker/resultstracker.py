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
import eventlet
import six

from collections import defaultdict
from kombu import Connection

from st2common.query.base import QueryContext
from st2common import log as logging
from st2common.models.db.executionstate import ActionExecutionStateDB
from st2common.persistence.executionstate import ActionExecutionState
from st2common.transport import consumers
from st2common.transport import utils as transport_utils
from st2common.runners.base import get_query_module
from st2common.transport.queues import RESULTSTRACKER_ACTIONSTATE_WORK_QUEUE

__all__ = [
    'ResultsTracker',
    'get_tracker'
]


LOG = logging.getLogger(__name__)


class ResultsTracker(consumers.MessageHandler):
    message_type = ActionExecutionStateDB

    def __init__(self, connection, queues):
        super(ResultsTracker, self).__init__(connection, queues)
        self._queriers = {}
        self._query_threads = []
        self._failed_imports = set()

    def start(self, wait=False):
        self._bootstrap()
        super(ResultsTracker, self).start(wait=wait)

    def wait(self):
        super(ResultsTracker, self).wait()
        for thread in self._query_threads:
            thread.wait()

    def shutdown(self):
        super(ResultsTracker, self).shutdown()
        LOG.info('Stats from queriers:')
        self._print_stats()

    def _print_stats(self):
        for _, querier in six.iteritems(self._queriers):
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

    def process(self, query_context):
        querier = self.get_querier(query_context.query_module)
        context = QueryContext.from_model(query_context)
        querier.add_queries(query_contexts=[context])
        return

    def get_querier(self, query_module_name):
        if (query_module_name not in self._queriers and
                query_module_name not in self._failed_imports):
            try:
                query_module = get_query_module(query_module_name)
            except:
                LOG.exception('Failed importing query module: %s', query_module_name)
                self._failed_imports.add(query_module_name)
                self._queriers[query_module_name] = None
            else:
                querier = query_module.get_instance()
                self._queriers[query_module_name] = querier
                self._query_threads.append(eventlet.spawn(querier.start))

        return self._queriers[query_module_name]


def get_tracker():
    with Connection(transport_utils.get_messaging_urls()) as conn:
        return ResultsTracker(conn, [RESULTSTRACKER_ACTIONSTATE_WORK_QUEUE])
