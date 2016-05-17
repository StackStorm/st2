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

from st2common.models.db.marker import DumperMarkerDB
from st2common.persistence.marker import DumperMarker
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.util import date as date_utils

from st2tests import DbTestCase


class DumperMarkerModelTest(DbTestCase):
    def test_dumper_marker_crud(self):
        saved = DumperMarkerModelTest._create_save_dumper_marker()
        retrieved = DumperMarker.get_by_id(saved.id)
        self.assertEqual(saved.marker, retrieved.marker,
                         'Same marker was not returned.')
        # test update
        time_now = date_utils.get_datetime_utc_now()
        retrieved.updated_at = time_now
        saved = DumperMarker.add_or_update(retrieved)
        retrieved = DumperMarker.get_by_id(saved.id)
        self.assertEqual(retrieved.updated_at, time_now, 'Update to marker failed.')
        # cleanup
        DumperMarkerModelTest._delete([retrieved])
        try:
            retrieved = DumperMarker.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, 'managed to retrieve after failure.')

    @staticmethod
    def _create_save_dumper_marker():
        created = DumperMarkerDB()
        created.marker = '2015-06-11T00:35:15.260439Z'
        created.updated_at = date_utils.get_datetime_utc_now()
        return DumperMarker.add_or_update(created)

    @staticmethod
    def _delete(model_objects):
        for model_object in model_objects:
            model_object.delete()
