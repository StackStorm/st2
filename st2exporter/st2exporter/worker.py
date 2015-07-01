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

import Queue

import eventlet
from kombu import Connection
from oslo_config import cfg

from st2common import log as logging
from st2common.constants.action import (LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED,
                                        LIVEACTION_STATUS_CANCELED)
from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.db.execution import ActionExecutionDB
from st2common.persistence.execution import ActionExecution
from st2common.persistence.marker import DumperMarker
from st2common.transport import consumers, execution, publishers
from st2common.util import isotime
from st2exporter.exporter.dumper import Dumper

__all__ = [
    'ExecutionsExporter'
]

COMPLETION_STATUSES = [LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED,
                       LIVEACTION_STATUS_CANCELED]
LOG = logging.getLogger(__name__)

EXPORTER_WORK_Q = execution.get_queue(
    'st2.exporter.work', routing_key=publishers.UPDATE_RK)


class ExecutionsExporter(consumers.MessageHandler):
    message_type = ActionExecutionDB

    def __init__(self, connection, queues):
        super(ExecutionsExporter, self).__init__(connection, queues)
        self.pending_executions = Queue.Queue()
        self._dumper = Dumper(queue=self.pending_executions,
                              export_dir=cfg.CONF.exporter.dump_dir)
        self._consumer_thread = None

    def start(self, wait=False):
        LOG.info('Bootstrapping executions from db...')
        try:
            self._bootstrap()
        except:
            LOG.exception('Unable to bootstrap executions from db. Aborting.')
            raise
        self._consumer_thread = eventlet.spawn(super(ExecutionsExporter, self).start, wait=True)
        self._dumper.start()
        if wait:
            self.wait()

    def wait(self):
        self._consumer_thread.wait()
        self._dumper.wait()

    def shutdown(self):
        self._dumper.stop()
        super(ExecutionsExporter, self).shutdown()

    def process(self, execution):
        LOG.debug('Got execution from queue: %s', execution)
        if execution.status not in COMPLETION_STATUSES:
            return
        execution_api = ActionExecutionAPI.from_model(execution, mask_secrets=True)
        self.pending_executions.put_nowait(execution_api)
        LOG.debug("Added execution to queue.")

    def _bootstrap(self):
        marker = self._get_export_marker_from_db()
        LOG.info('Using marker %s...' % marker)
        missed_executions = self._get_missed_executions_from_db(export_marker=marker)
        LOG.info('Found %d executions not exported yet...', len(missed_executions))

        for missed_execution in missed_executions:
            if missed_execution.status not in COMPLETION_STATUSES:
                continue
            execution_api = ActionExecutionAPI.from_model(missed_execution, mask_secrets=True)
            try:
                LOG.debug('Missed execution %s', execution_api)
                self.pending_executions.put_nowait(execution_api)
            except:
                LOG.exception('Failed adding execution to in-memory queue.')
                continue
        LOG.info('Bootstrapped executions...')

    def _get_export_marker_from_db(self):
        try:
            markers = DumperMarker.get_all()
        except:
            return None
        else:
            if len(markers) >= 1:
                marker = markers[0]
                return isotime.parse(marker.marker)
            else:
                return None

    def _get_missed_executions_from_db(self, export_marker=None):
        if not export_marker:
            return self._get_all_executions_from_db()

        # XXX: Should adapt this query to get only executions with status
        # in COMPLETION_STATUSES.
        filters = {'end_timestamp__gt': export_marker}
        LOG.info('Querying for executions with filters: %s', filters)
        return ActionExecution.query(**filters)

    def _get_all_executions_from_db(self):
        return ActionExecution.get_all()  # XXX: Paginated call.


def get_worker():
    with Connection(cfg.CONF.messaging.url) as conn:
        return ExecutionsExporter(conn, [EXPORTER_WORK_Q])
