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

from __future__ import absolute_import

from st2common.constants.sensors import SENSOR_STATUS_RUNNING
from st2common.constants.sensors import SENSOR_STATUS_STOPPED
from st2common.constants.sensors import SENSOR_STATUS_ABANDONED
from st2common.models.db.sensor_instance import SensorInstanceDB
from st2common.persistence.sensor_instance import SensorInstance

from st2tests import DbTestCase
from st2tests.base import CleanDbTestCase

from tests.unit.base import BaseDBModelCRUDTestCase

__all__ = ["SensorInstanceDBModelCRUDTestCase", "SensorInstanceQueryTestCase"]


class SensorInstanceDBModelCRUDTestCase(BaseDBModelCRUDTestCase, DbTestCase):
    model_class = SensorInstanceDB
    persistance_class = SensorInstance
    model_class_kwargs = {
        "ref": "wolfpack.StupidSensor",
        "pack": "wolfpack",
        "status": SENSOR_STATUS_RUNNING,
        "hostname": "sensor-node-1",
        "pid": 1234,
        "exit_code": 0,
        "respawn_count": 0,
    }
    update_attribute_name = "status"
    # updated_at is populated by a default callable, not part of the kwargs.
    skip_check_attribute_names = ["updated_at"]


class SensorInstanceQueryTestCase(CleanDbTestCase):
    def _create(self, ref, pack, status, **kwargs):
        instance_db = SensorInstanceDB(ref=ref, pack=pack, status=status, **kwargs)
        return SensorInstance.add_or_update(instance_db)

    def test_query_by_ref(self):
        self._create("wolfpack.SensorA", "wolfpack", SENSOR_STATUS_RUNNING, pid=10)
        self._create("wolfpack.SensorB", "wolfpack", SENSOR_STATUS_STOPPED)

        instance_db = SensorInstance.query(ref="wolfpack.SensorA").first()
        self.assertIsNotNone(instance_db)
        self.assertEqual(instance_db.ref, "wolfpack.SensorA")
        self.assertEqual(instance_db.status, SENSOR_STATUS_RUNNING)
        self.assertEqual(instance_db.pid, 10)

    def test_query_by_status(self):
        self._create("wolfpack.SensorA", "wolfpack", SENSOR_STATUS_RUNNING)
        self._create("wolfpack.SensorB", "wolfpack", SENSOR_STATUS_ABANDONED)
        self._create("wolfpack.SensorC", "wolfpack", SENSOR_STATUS_ABANDONED)

        abandoned = list(SensorInstance.query(status=SENSOR_STATUS_ABANDONED))
        self.assertEqual(len(abandoned), 2)
        refs = sorted(instance.ref for instance in abandoned)
        self.assertEqual(refs, ["wolfpack.SensorB", "wolfpack.SensorC"])

    def test_status_transition_upsert_by_ref(self):
        # Simulate the container upsert pattern: look up by ref, mutate in place,
        # persist - the record count stays at one and the id is stable.
        ref = "wolfpack.SensorA"
        created = self._create(ref, "wolfpack", SENSOR_STATUS_RUNNING, pid=99)

        instance_db = SensorInstance.query(ref=ref).first()
        instance_db.status = SENSOR_STATUS_ABANDONED
        instance_db.exit_code = 1
        instance_db.respawn_count = 2
        updated = SensorInstance.add_or_update(instance_db)

        self.assertEqual(created.id, updated.id)
        self.assertEqual(SensorInstance.query(ref=ref).count(), 1)
        self.assertEqual(updated.status, SENSOR_STATUS_ABANDONED)
        self.assertEqual(updated.exit_code, 1)
        self.assertEqual(updated.respawn_count, 2)
