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

import eventlet
from oslo.config import cfg

from st2exporter.exporter.file_writer import TextFileWriter
from st2exporter.exporter.json_converter import JsonConverter

ALLOWED_EXTENSIONS = ['json']

CONVERTERS = {
    'json': JsonConverter
}


class Dumper(object):

    def __init__(self, queue=None, files_dir=None, file_format='json',
                 file_prefix='st2-executions-',
                 batch_size=1000, sleep_interval=60,
                 max_files_per_sleep=5,
                 file_writer=None):
        if not queue:
            raise Exception('Need a queue to consume data from.')

        if not files_dir:
            self._files_dir = cfg.CONF.exporter.dump_dir

        if not os.path.exists(self._files_dir):
            raise Exception('Dir path %s does not exist. Create one before using exporter.' %
                            self._files_dir)

        self._file_format = file_format.lower()
        if self._file_format not in ALLOWED_EXTENSIONS:
            return ValueError('Disallowed extension %s.' % file_format)

        self._file_prefix = file_prefix
        self._batch_size = batch_size
        self._max_files_per_sleep = max_files_per_sleep
        self._queue = queue
        self._consume_thread = None
        self._sleep_interval = sleep_interval
        self._converter = CONVERTERS[self._file_format]()

        if not file_writer:
            self._file_writer = TextFileWriter()

    def start(self):
        self._consume_thread = eventlet.spawn(self._write_to_disk)

    def stop(self):
        return eventlet.kill(self._consume_thread)

    def _get_batch(self):
        if self._queue.qsize() <= 0:
            return None

        executions_to_write = []
        for count in self.batch_size:
            executions_to_write = []
            try:
                item = self._queue.get()
            except:
                break
            else:
                executions_to_write.append(item)
        return executions_to_write

    def _write_to_disk(self):
        if self._queue.qsize() <= 0:
            eventlet.sleep(self._sleep_interval)

        for count in self._max_files_per_sleep:
            batch = self._get_batch()
            if not batch:
                break
            self._write_batch_to_disk(batch)
        eventlet.sleep(self._sleep_interval)

    def _write_batch_to_disk(self, batch):
        doc_to_write = self._converter.convert(batch)
        self._file_writer.write_text(doc_to_write, self._get_file_name())

    def _get_file_name(self):
        timestring = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        file_name = os.path.join(self._files_dir, self._file_prefix + timestring)
        return file_name
