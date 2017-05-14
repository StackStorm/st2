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

import abc
import eventlet
from oslo_config import cfg
import six

from st2common import log as logging
from st2exporter.exporter.dumper import Dumper
from st2common.persistence.marker import DumperMarker
from st2common.transport import consumers
from st2common.util import isotime

__all__ = [
    'ModelExporter'
]

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class ModelExporter(consumers.MessageHandler):
    api_model = None
    persistence_model = None

    def __init__(self, model_type, connection, queues):
        super(ModelExporter, self).__init__(connection, queues)
        self.pending_models = Queue.Queue()
        self._dumper = Dumper(queue=self.pending_models,
                              export_dir=cfg.CONF.exporter.dump_dir)
        self._consumer_thread = None
        self._model_type = model_type
        if not self.api_model or not self.persistence_model:
            raise Exception('No API or persistence model defined for exporter.')

    def start(self, wait=False):
        LOG.info('Starting model exporter -- %s.', self._model_type)
        try:
            self.bootstrap()
        except:
            LOG.info('Failed bootstrap for model -- %s', self._model_type)
            raise
        self._consumer_thread = eventlet.spawn(super(ModelExporter, self).start, wait=True)
        self._dumper.start()
        if wait:
            self.wait()

    def wait(self):
        self._consumer_thread.wait()
        self._dumper.wait()

    def shutdown(self):
        self._dumper.stop()
        super(ModelExporter, self).shutdown()

    def process(self, db_model):
        LOG.debug('Got model from queue: %s', db_model)
        if self.should_export(db_model):
            model_api = self.api_model.from_model(db_model, mask_secrets=True)
            self.pending_models.put_nowait(model_api)
            LOG.debug("Added execution to queue.")

    def bootstrap(self):
        marker = self._get_export_marker_from_db()
        LOG.info('Using marker %s...' % marker)
        missed_models = self.get_missed_models_from_db(export_marker=marker)
        LOG.info('Found %d models not exported yet...', len(missed_models))

        for missed_model in missed_models:
            if not self.should_export(missed_model):
                continue
            model_api = self.api_model.from_model(missed_model, mask_secrets=True)
            try:
                LOG.debug('Missed execution %s', model_api)
                self.pending_models.put_nowait(model_api)
            except:
                LOG.exception('Failed adding execution to in-memory queue.')
                continue
        LOG.info('Bootstrapped models...')

    def should_export(self, db_model):
        return True

    def get_missed_models_from_db(self, export_marker=None):
        if not export_marker:
            return self._get_all_models_from_db()

        # XXX: Should adapt this query to get only executions with status
        # in COMPLETION_STATUSES.
        filters = {'end_timestamp__gt': export_marker}
        LOG.info('Querying for executions with filters: %s', filters)
        return ModelExporter.persistence_model.query(**filters)

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

    def _get_all_models_from_db(self):
        return self.persistence_model.get_all()
