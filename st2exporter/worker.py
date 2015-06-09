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

import datetime
import Queue

from kombu import Connection
from oslo.config import cfg

from st2actions.container.base import RunnerContainer
from st2common import log as logging
from st2common.models.db.execution import ActionExecutionDB
from st2common.persistence.execution import ActionExecution
from st2common.transport import consumers, execution, publishers
from st2common.util import isotime


LOG = logging.getLogger(__name__)

EXPORTER_WORK_Q = execution.get_queue(
    'st2.exporter.work', routing_key=publishers.UPDATE_RK)


class ExecutionsExporter(consumers.MessageHandler):
    message_type = ActionExecutionDB

    def __init__(self, connection, queues):
        super(ExecutionsExporter, self).__init__(connection, queues)
        self.container = RunnerContainer()
        self.persisted_timestamp = None
        self.pending_executions = Queue.Queue()

    def start(self, wait=False):
        self._bootstrap()
        super(ExecutionsExporter, self).start(wait=wait)

    def shutdown(self):
        super(ExecutionsExporter, self).shutdown()

    def process(self, execution):
        pass

    def _bootstrap(self):
        marker = self._get_export_marker_from_db()
        missed_executions = self._get_missed_executions_from_db(export_marker=marker)

        for missed_execution in missed_executions:
            try:
                self.pending_executions.put_nowait(missed_execution)
            except:
                LOG.exception('Failed adding execution to in-memory queue.')
                continue

    def _get_export_marker_from_db(self):
        # XXX: Document model seems excessive for this.
        # XXX: Needs a notion of `node` based marker because distributed.
        return None

    def _update_export_marker(self):
        # XXX: Should write marker to db.
        pass

    def _get_missed_executions_from_db(self, export_marker=None):
        if not export_marker:
            return self._get_all_executions_from_db()

        now = datetime.datetime.now()
        filters = {'start_timestamp__gt': isotime.parse(export_marker),
                   'start_timestamp__lt': now}
        return ActionExecution.query(**filters)

    def _get_all_executions_from_db(self):
        return ActionExecution.get_all()  # XXX: Paginated call.


def get_worker():
    with Connection(cfg.CONF.messaging.url) as conn:
        return ExecutionsExporter(conn, [EXPORTER_WORK_Q])
