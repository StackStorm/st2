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

from st2common import log as logging
from st2common.transport import execution, publishers
from st2common.transport import utils as transport_utils
from st2exporter.consumers.execution import ExecutionsExporter


EXPORTER_WORK_Q = execution.get_queue(
    'st2.exporter.work', routing_key=publishers.UPDATE_RK)
LOG = logging.getLogger(__name__)


class Exporter(object):
    def __init__(self):
        self._model_exporters = []

        self._executions_exporter = None
        with Connection(transport_utils.get_messaging_urls()) as conn:
            self._executions_exporter = ExecutionsExporter(conn, [EXPORTER_WORK_Q])

        self._model_exporters.append(self._executions_exporter)
        LOG.info('Available model exporters %s.', self._model_exporters)
        self._model_exporters_pool = eventlet.GreenPool(len(self._model_exporters))
        self._stopped = False

    def start(self, wait=False):
        LOG.info('Starting model exporters...')
        for model_exporter in self._model_exporters:
            while self._model_exporters_pool.free() <= 0 and not self._stopped:
                eventlet.sleep(0.1)
            if not self._stopped:
                try:
                    self._model_exporters_pool.spawn(model_exporter.start, wait=False)
                except:
                    LOG.exception('Failed to start model exporter %s.', model_exporter)
        self._model_exporters_pool.waitall()

        if wait:
            self.wait()

    def shutdown(self):
        for model_exporter in self._model_exporters:
            while not self._model_exporters_pool.free():
                eventlet.sleep(0.1)
            try:
                self._model_exporters_pool.spawn(model_exporter.shutdown)
            except:
                LOG.exception('Failed shutting down model exporter %s.', model_exporter)
        self._stopped = True

    def wait(self):
        for model_exporter in self._model_exporters:
            model_exporter.wait()
            LOG.info('Model exporter %s quit.', model_exporter)
            # XXX: We should probably raising an exception at this point.


def get_worker():
    return Exporter()
