# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import eventlet
from six.moves import queue

from st2common import log as logging
from st2exporter.exporter.file_writer import TextFileWriter
from st2exporter.exporter.json_converter import JsonConverter
from st2common.models.db.marker import DumperMarkerDB
from st2common.persistence.marker import DumperMarker
from st2common.util import date as date_utils
from st2common.util import isotime

__all__ = ["Dumper"]

ALLOWED_EXTENSIONS = ["json"]

CONVERTERS = {"json": JsonConverter}

LOG = logging.getLogger(__name__)


class Dumper(object):
    def __init__(
        self,
        queue,
        export_dir,
        file_format="json",
        file_prefix="st2-executions-",
        batch_size=1000,
        sleep_interval=60,
        max_files_per_sleep=5,
        file_writer=None,
    ):
        if not queue:
            raise Exception("Need a queue to consume data from.")

        if not export_dir:
            raise Exception("Export dir needed to dump files to.")

        self._export_dir = export_dir
        if not os.path.exists(self._export_dir):
            raise Exception(
                "Dir path %s does not exist. Create one before using exporter."
                % self._export_dir
            )

        self._file_format = file_format.lower()
        if self._file_format not in ALLOWED_EXTENSIONS:
            raise ValueError("Disallowed extension %s." % file_format)

        self._file_prefix = file_prefix
        self._batch_size = batch_size
        self._max_files_per_sleep = max_files_per_sleep
        self._queue = queue
        self._flush_thread = None
        self._sleep_interval = sleep_interval
        self._converter = CONVERTERS[self._file_format]()
        self._shutdown = False
        self._persisted_marker = None

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
        for _ in range(self._batch_size):
            try:
                item = self._queue.get(block=False)
            except queue.Empty:
                break
            else:
                executions_to_write.append(item)

        LOG.debug("Returning %d items in batch.", len(executions_to_write))
        LOG.debug("Remaining items in queue: %d", self._queue.qsize())
        return executions_to_write

    def _flush(self):
        while not self._shutdown:
            while self._queue.empty():
                eventlet.sleep(self._sleep_interval)

            try:
                self._write_to_disk()
            except:
                LOG.error("Failed writing data to disk.")

    def _write_to_disk(self):
        count = 0
        self._create_date_folder()

        for _ in range(self._max_files_per_sleep):
            batch = self._get_batch()

            if not batch:
                return count

            try:
                self._write_batch_to_disk(batch)
                self._update_marker(batch)
                count += 1
            except:
                LOG.exception("Writing batch to disk failed.")
        return count

    def _create_date_folder(self):
        folder_name = self._get_date_folder()
        folder_path = os.path.join(self._export_dir, folder_name)

        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
            except:
                LOG.exception("Unable to create sub-folder %s for export.", folder_name)
                raise

    def _write_batch_to_disk(self, batch):
        doc_to_write = self._converter.convert(batch)
        self._file_writer.write_text(doc_to_write, self._get_file_name())

    def _get_file_name(self):
        timestring = date_utils.get_datetime_utc_now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        file_name = self._file_prefix + timestring + "." + self._file_format
        file_name = os.path.join(self._export_dir, self._get_date_folder(), file_name)
        return file_name

    def _get_date_folder(self):
        return date_utils.get_datetime_utc_now().strftime("%Y-%m-%d")

    def _update_marker(self, batch):
        timestamps = [isotime.parse(item.end_timestamp) for item in batch]
        new_marker = max(timestamps)

        if self._persisted_marker and self._persisted_marker > new_marker:
            LOG.warn(
                "Older executions are being exported. Perhaps out of order messages."
            )

        try:
            self._write_marker_to_db(new_marker)
        except:
            LOG.exception("Failed persisting dumper marker to db.")
        else:
            self._persisted_marker = new_marker

        return self._persisted_marker

    def _write_marker_to_db(self, new_marker):
        LOG.info("Updating marker in db to: %s", new_marker)
        markers = DumperMarker.get_all()

        if len(markers) > 1:
            LOG.exception("More than one dumper marker found. Using first found one.")

        marker = isotime.format(new_marker, offset=False)
        updated_at = date_utils.get_datetime_utc_now()

        if markers:
            marker_id = markers[0]["id"]
        else:
            marker_id = None

        marker_db = DumperMarkerDB(id=marker_id, marker=marker, updated_at=updated_at)
        return DumperMarker.add_or_update(marker_db)
