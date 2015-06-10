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

import eventlet
from kombu import Connection
from oslo.config import cfg

from st2common import log as logging
from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.db.execution import ActionExecutionDB
from st2common.persistence.execution import ActionExecution
from st2common.transport import consumers, execution, publishers
from st2common.util import isotime
from st2common.util.jsonify import json_encode
from st2exporter.exporter.dumper import Dumper

LOG = logging.getLogger(__name__)

EXPORTER_WORK_Q = execution.get_queue(
    'st2.exporter.work', routing_key=publishers.UPDATE_RK)


class ExecutionsExporter(consumers.MessageHandler):
    message_type = ActionExecutionDB

    def __init__(self, connection, queues):
        super(ExecutionsExporter, self).__init__(connection, queues)
        self._persisted_timestamp = None
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
        execution_api = ActionExecutionAPI.from_model(execution)
        execution_json = json_encode(execution_api)
        LOG.info('Got execution %s.', execution_json)
        self.pending_executions.put_nowait(execution_json)

    def _bootstrap(self):
        marker = self._get_export_marker_from_db()
        LOG.info('Using marker %s...' % marker)
        missed_executions = self._get_missed_executions_from_db(export_marker=marker)
        LOG.info('Found %d executions not exported yet...', len(missed_executions))

        for missed_execution in missed_executions:
            execution_json = json_encode(ActionExecutionAPI.from_model(missed_execution))
            try:
                LOG.debug('Missed execution %s', execution_json)
                self.pending_executions.put_nowait(execution_json)
            except:
                LOG.exception('Failed adding execution to in-memory queue.')
                continue
        LOG.info('Bootstrapped executions...')

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
