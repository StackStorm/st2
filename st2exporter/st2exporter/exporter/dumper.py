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
import os
import Queue

import eventlet

from st2common import log as logging
from st2exporter.exporter.file_writer import TextFileWriter
from st2exporter.exporter.json_converter import JsonConverter

ALLOWED_EXTENSIONS = ['json']

CONVERTERS = {
    'json': JsonConverter
}

LOG = logging.getLogger(__name__)


class Dumper(object):

    def __init__(self, queue=None, export_dir=None, file_format='json',
                 file_prefix='st2-executions-',
                 batch_size=1000, sleep_interval=1,
                 max_files_per_sleep=5,
                 file_writer=None):
        if not queue:
            raise Exception('Need a queue to consume data from.')

        if not export_dir:
            raise Exception('Export dir needed to dump files to.')

        self._export_dir = export_dir
        if not os.path.exists(self._export_dir):
            raise Exception('Dir path %s does not exist. Create one before using exporter.' %
                            self._export_dir)

        self._file_format = file_format.lower()
        if self._file_format not in ALLOWED_EXTENSIONS:
            return ValueError('Disallowed extension %s.' % file_format)

        self._file_prefix = file_prefix
        self._batch_size = batch_size
        self._max_files_per_sleep = max_files_per_sleep
        self._queue = queue
        self._flush_thread = None
        self._sleep_interval = sleep_interval
        self._converter = CONVERTERS[self._file_format]()
        self._shutdown = False

        if not file_writer:
            self._file_writer = TextFileWriter()

    def start(self, wait=False):
        self._flush_thread = eventlet.spawn(self._flush)
        if wait:
            self.wait()

    def wait(self):
        self._flush_thread.wait()

    def stop(self):
        self._shutdown = True
        return eventlet.kill(self._flush_thread)

    def _get_batch(self):
        if self._queue.empty():
            return None

        executions_to_write = []
        for count in range(self._batch_size):
            try:
                item = self._queue.get(block=False)
            except Queue.Empty:
                break
            else:
                executions_to_write.append(item)

        LOG.debug('Returning %d items in batch.', len(executions_to_write))
        LOG.debug('Remaining items in queue: %d', self._queue.qsize())
        return executions_to_write

    def _flush(self):
        while not self._shutdown:
            while self._queue.empty():
                eventlet.sleep(self._sleep_interval)

            self._write_to_disk()

    def _write_to_disk(self):
        batch = self._get_batch()

        if not batch:
            return

        try:
            self._write_batch_to_disk(batch)
        except:
            LOG.exception('Writing batch to disk failed.')

    def _write_batch_to_disk(self, batch):
        doc_to_write = self._converter.convert(batch)
        self._file_writer.write_text(doc_to_write, self._get_file_name())

    def _get_file_name(self):
        timestring = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        file_name = self._file_prefix + timestring + '.' + self._file_format
        file_name = os.path.join(self._export_dir, file_name)
        return file_name
