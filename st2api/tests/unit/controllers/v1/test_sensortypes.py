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

import copy

import six

import st2common.bootstrap.sensorsregistrar as sensors_registrar
from st2api.controllers.v1.sensors import SensorTypeController

from st2common.constants.sensors import SENSOR_STATUS_RUNNING
from st2common.constants.sensors import SENSOR_STATUS_ABANDONED
from st2common.models.db.sensor_instance import SensorInstanceDB
from st2common.persistence.sensor_instance import SensorInstance

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

from st2tests.fixtures.packs.dummy_pack_1.fixture import (
    PACK_NAME as DUMMY_PACK_1,
)

http_client = six.moves.http_client

__all__ = ["SensorTypeControllerTestCase"]


class SensorTypeControllerTestCase(
    FunctionalTest, APIControllerWithIncludeAndExcludeFilterTestCase
):
    get_all_path = "/v1/sensortypes"
    controller_cls = SensorTypeController
    include_attribute_field_name = "entry_point"
    exclude_attribute_field_name = "artifact_uri"
    test_exact_object_count = False

    @classmethod
    def setUpClass(cls):
        super(SensorTypeControllerTestCase, cls).setUpClass()

        # Register local sensor and pack fixtures
        sensors_registrar.register_sensors(use_pack_cache=False)

    def test_get_all_and_minus_one(self):
        resp = self.app.get("/v1/sensortypes")
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 3)
        self.assertEqual(resp.json[0]["name"], "SampleSensor")

        resp = self.app.get("/v1/sensortypes/?limit=-1")
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 3)
        self.assertEqual(resp.json[0]["name"], "SampleSensor")

    def test_get_all_negative_limit(self):
        resp = self.app.get("/v1/sensortypes/?limit=-22", expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(
            resp.json["faultstring"],
            'Limit, "-22" specified, must be a positive number.',
        )

    def test_get_all_filters(self):
        resp = self.app.get("/v1/sensortypes")
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 3)

        # ?name filter
        resp = self.app.get("/v1/sensortypes?name=foobar")
        self.assertEqual(len(resp.json), 0)

        resp = self.app.get("/v1/sensortypes?name=SampleSensor2")
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]["name"], "SampleSensor2")
        self.assertEqual(resp.json[0]["ref"], f"{DUMMY_PACK_1}.SampleSensor2")

        resp = self.app.get("/v1/sensortypes?name=SampleSensor3")
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]["name"], "SampleSensor3")

        # ?pack filter
        resp = self.app.get("/v1/sensortypes?pack=foobar")
        self.assertEqual(len(resp.json), 0)

        resp = self.app.get(f"/v1/sensortypes?pack={DUMMY_PACK_1}")
        self.assertEqual(len(resp.json), 3)

        # ?enabled filter
        resp = self.app.get("/v1/sensortypes?enabled=False")
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]["enabled"], False)

        resp = self.app.get("/v1/sensortypes?enabled=True")
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]["enabled"], True)
        self.assertEqual(resp.json[1]["enabled"], True)

        # ?trigger filter
        resp = self.app.get(f"/v1/sensortypes?trigger={DUMMY_PACK_1}.event3")
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]["trigger_types"], [f"{DUMMY_PACK_1}.event3"])

        resp = self.app.get(f"/v1/sensortypes?trigger={DUMMY_PACK_1}.event")
        self.assertEqual(len(resp.json), 2)
        self.assertEqual(resp.json[0]["trigger_types"], [f"{DUMMY_PACK_1}.event"])
        self.assertEqual(resp.json[1]["trigger_types"], [f"{DUMMY_PACK_1}.event"])

    def test_get_one_success(self):
        resp = self.app.get(f"/v1/sensortypes/{DUMMY_PACK_1}.SampleSensor")
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(resp.json["name"], "SampleSensor")
        self.assertEqual(resp.json["ref"], f"{DUMMY_PACK_1}.SampleSensor")

    def test_get_one_doesnt_exist(self):
        resp = self.app.get("/v1/sensortypes/1", expect_errors=True)
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)

    def tearDown(self):
        super(SensorTypeControllerTestCase, self).tearDown()
        # Remove any runtime health records created by health tests so they do
        # not leak into other tests.
        for instance in SensorInstance.get_all():
            SensorInstance.delete(instance)

    @staticmethod
    def _create_health_record(ref, pack, status, **kwargs):
        instance_db = SensorInstanceDB(ref=ref, pack=pack, status=status, **kwargs)
        return SensorInstance.add_or_update(instance_db)

    def test_get_one_merges_health_fields(self):
        ref = f"{DUMMY_PACK_1}.SampleSensor"
        self._create_health_record(
            ref,
            DUMMY_PACK_1,
            SENSOR_STATUS_RUNNING,
            hostname="sensor-node-1",
            pid=4321,
            exit_code=0,
            respawn_count=0,
        )

        resp = self.app.get(f"/v1/sensortypes/{ref}")
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(resp.json["status"], SENSOR_STATUS_RUNNING)
        self.assertEqual(resp.json["hostname"], "sensor-node-1")
        self.assertEqual(resp.json["pid"], 4321)
        self.assertEqual(resp.json["exit_code"], 0)
        self.assertEqual(resp.json["respawn_count"], 0)
        self.assertIsNotNone(resp.json["updated_at"])

    def test_get_one_no_health_record_returns_null_fields(self):
        # A sensor which has never run has no SensorInstanceDB record; the
        # health fields must still be present and null.
        resp = self.app.get(f"/v1/sensortypes/{DUMMY_PACK_1}.SampleSensor")
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertIsNone(resp.json["status"])
        self.assertIsNone(resp.json["hostname"])
        self.assertIsNone(resp.json["pid"])
        self.assertIsNone(resp.json["updated_at"])

    def test_get_all_merges_health_fields(self):
        running_ref = f"{DUMMY_PACK_1}.SampleSensor"
        abandoned_ref = f"{DUMMY_PACK_1}.SampleSensor2"
        self._create_health_record(
            running_ref, DUMMY_PACK_1, SENSOR_STATUS_RUNNING, pid=100
        )
        self._create_health_record(
            abandoned_ref, DUMMY_PACK_1, SENSOR_STATUS_ABANDONED, exit_code=1
        )

        resp = self.app.get("/v1/sensortypes")
        self.assertEqual(resp.status_int, http_client.OK)
        status_by_ref = {item["ref"]: item["status"] for item in resp.json}
        self.assertEqual(status_by_ref[running_ref], SENSOR_STATUS_RUNNING)
        self.assertEqual(status_by_ref[abandoned_ref], SENSOR_STATUS_ABANDONED)
        # Sensor without a health record reports a null status.
        self.assertIsNone(status_by_ref[f"{DUMMY_PACK_1}.SampleSensor3"])

    def test_get_all_status_filter(self):
        running_ref = f"{DUMMY_PACK_1}.SampleSensor"
        abandoned_ref = f"{DUMMY_PACK_1}.SampleSensor2"
        self._create_health_record(running_ref, DUMMY_PACK_1, SENSOR_STATUS_RUNNING)
        self._create_health_record(abandoned_ref, DUMMY_PACK_1, SENSOR_STATUS_ABANDONED)

        resp = self.app.get("/v1/sensortypes?status=abandoned")
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]["ref"], abandoned_ref)
        self.assertEqual(resp.json[0]["status"], SENSOR_STATUS_ABANDONED)

    def test_get_all_status_filter_no_matches(self):
        # No sensor is in the requested status - the result is empty.
        resp = self.app.get("/v1/sensortypes?status=abandoned")
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 0)

    def test_get_all_include_attributes_with_health_fields(self):
        # The CLI (st2 sensor list) requests health fields via include_attributes.
        # They are not SensorTypeDB fields, so they must be stripped before the
        # query (otherwise mongoengine 400s) and still merged in from the health
        # record afterwards. This mirrors the request st2-self-check issues.
        running_ref = f"{DUMMY_PACK_1}.SampleSensor"
        self._create_health_record(
            running_ref, DUMMY_PACK_1, SENSOR_STATUS_RUNNING, pid=100
        )

        resp = self.app.get(
            "/v1/sensortypes?include_attributes=ref,pack,enabled,status,updated_at"
        )
        self.assertEqual(resp.status_int, http_client.OK)
        item_by_ref = {item["ref"]: item for item in resp.json}
        # DB-backed included field is present.
        self.assertIn("pack", item_by_ref[running_ref])
        # Synthetic health fields are merged in even though they were stripped
        # from the DB query.
        self.assertEqual(item_by_ref[running_ref]["status"], SENSOR_STATUS_RUNNING)
        self.assertIsNotNone(item_by_ref[running_ref]["updated_at"])

    def test_disable_and_enable_sensor(self):
        # Verify initial state
        resp = self.app.get(f"/v1/sensortypes/{DUMMY_PACK_1}.SampleSensor")
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertTrue(resp.json["enabled"])

        sensor_data = resp.json

        # Disable sensor
        data = copy.deepcopy(sensor_data)
        data["enabled"] = False
        put_resp = self.app.put_json(
            f"/v1/sensortypes/{DUMMY_PACK_1}.SampleSensor", data
        )
        self.assertEqual(put_resp.status_int, http_client.OK)
        self.assertEqual(put_resp.json["ref"], f"{DUMMY_PACK_1}.SampleSensor")
        self.assertFalse(put_resp.json["enabled"])

        # Verify sensor has been disabled
        resp = self.app.get(f"/v1/sensortypes/{DUMMY_PACK_1}.SampleSensor")
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertFalse(resp.json["enabled"])

        # Enable sensor
        data = copy.deepcopy(sensor_data)
        data["enabled"] = True
        put_resp = self.app.put_json(
            f"/v1/sensortypes/{DUMMY_PACK_1}.SampleSensor", data
        )
        self.assertEqual(put_resp.status_int, http_client.OK)
        self.assertTrue(put_resp.json["enabled"])

        # Verify sensor has been enabled
        resp = self.app.get(f"/v1/sensortypes/{DUMMY_PACK_1}.SampleSensor")
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertTrue(resp.json["enabled"])
