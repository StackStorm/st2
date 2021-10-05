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

import os
import sys
import signal

from st2common import log as logging
from st2common.util import concurrency
from st2reactor.container.process_container import ProcessSensorContainer
from st2common.services.sensor_watcher import SensorWatcher
from st2common.models.system.common import ResourceReference

LOG = logging.getLogger(__name__)

__all__ = ["SensorContainerManager"]


class SensorContainerManager(object):
    def __init__(self, sensors_partitioner, single_sensor_mode=False):
        if not sensors_partitioner:
            raise ValueError("sensors_partitioner should be non-None.")

        self._sensors_partitioner = sensors_partitioner
        self._single_sensor_mode = single_sensor_mode

        self._sensor_container = None
        self._container_thread = None

        self._sensors_watcher = SensorWatcher(
            create_handler=self._handle_create_sensor,
            update_handler=self._handle_update_sensor,
            delete_handler=self._handle_delete_sensor,
            queue_suffix="sensor_container",
        )

    def run_sensors(self):
        """
        Run all sensors as determined by sensors_partitioner.
        """
        sensors = self._sensors_partitioner.get_sensors()
        if sensors:
            LOG.info("Setting up container to run %d sensors.", len(sensors))
            LOG.info(
                "\tSensors list - %s.",
                [self._get_sensor_ref(sensor) for sensor in sensors],
            )

        sensors_to_run = []
        for sensor in sensors:
            # TODO: Directly pass DB object to the ProcessContainer
            sensors_to_run.append(self._to_sensor_object(sensor))

        LOG.info("(PID:%s) SensorContainer started.", os.getpid())
        self._setup_sigterm_handler()

        exit_code = self._spin_container_and_wait(sensors_to_run)
        return exit_code

    def _spin_container_and_wait(self, sensors):
        exit_code = 0

        try:
            self._sensor_container = ProcessSensorContainer(
                sensors=sensors, single_sensor_mode=self._single_sensor_mode
            )
            self._container_thread = concurrency.spawn(self._sensor_container.run)

            LOG.debug("Starting sensor CUD watcher...")
            self._sensors_watcher.start()

            exit_code = self._container_thread.wait()
            LOG.error("Process container quit with exit_code %d.", exit_code)
            LOG.error("(PID:%s) SensorContainer stopped.", os.getpid())
        except (KeyboardInterrupt, SystemExit):
            self._sensor_container.shutdown()
            self._sensors_watcher.stop()

            LOG.info(
                "(PID:%s) SensorContainer stopped. Reason - %s",
                os.getpid(),
                sys.exc_info()[0].__name__,
            )

            concurrency.kill(self._container_thread)
            self._container_thread = None

            return exit_code

        return exit_code

    def _setup_sigterm_handler(self):
        def sigterm_handler(signum=None, frame=None):
            # This will cause SystemExit to be throw and we call sensor_container.shutdown()
            # there which cleans things up.
            sys.exit(0)

        # Register a SIGTERM signal handler which calls sys.exit which causes SystemExit to
        # be thrown. We catch SystemExit and handle cleanup there.
        signal.signal(signal.SIGTERM, sigterm_handler)

    def _to_sensor_object(self, sensor_db):
        file_path = sensor_db.artifact_uri.replace("file://", "")
        class_name = sensor_db.entry_point.split(".")[-1]

        sensor_obj = {
            "pack": sensor_db.pack,
            "file_path": file_path,
            "class_name": class_name,
            "trigger_types": sensor_db.trigger_types,
            "poll_interval": sensor_db.poll_interval,
            "ref": self._get_sensor_ref(sensor_db),
        }

        return sensor_obj

    #################################################
    # Event handler methods for the sensor CUD events
    #################################################

    def _handle_create_sensor(self, sensor):
        if not self._sensors_partitioner.is_sensor_owner(sensor):
            LOG.info(
                "sensor %s is not supported. Ignoring create.",
                self._get_sensor_ref(sensor),
            )
            return
        if not sensor.enabled:
            LOG.info("sensor %s is not enabled.", self._get_sensor_ref(sensor))
            return
        LOG.info("Adding sensor %s.", self._get_sensor_ref(sensor))
        self._sensor_container.add_sensor(sensor=self._to_sensor_object(sensor))

    def _handle_update_sensor(self, sensor):
        if not self._sensors_partitioner.is_sensor_owner(sensor):
            LOG.info(
                "sensor %s is not assigned to this partition. Ignoring update. ",
                self._get_sensor_ref(sensor),
            )
            return
        sensor_ref = self._get_sensor_ref(sensor)
        sensor_obj = self._to_sensor_object(sensor)

        # Handle disabling sensor
        if not sensor.enabled:
            LOG.info("Sensor %s disabled. Unloading sensor.", sensor_ref)
            self._sensor_container.remove_sensor(sensor=sensor_obj)
            return

        LOG.info("Sensor %s updated. Reloading sensor.", sensor_ref)
        try:
            self._sensor_container.remove_sensor(sensor=sensor_obj)
        except:
            LOG.exception("Failed to reload sensor %s", sensor_ref)
        else:
            self._sensor_container.add_sensor(sensor=sensor_obj)
            LOG.info("Sensor %s reloaded.", sensor_ref)

    def _handle_delete_sensor(self, sensor):
        if not self._sensors_partitioner.is_sensor_owner(sensor):
            LOG.info(
                "sensor %s is not supported. Ignoring delete.",
                self._get_sensor_ref(sensor),
            )
            return
        LOG.info("Unloading sensor %s.", self._get_sensor_ref(sensor))
        self._sensor_container.remove_sensor(sensor=self._to_sensor_object(sensor))

    def _get_sensor_ref(self, sensor):
        return ResourceReference.to_string_reference(pack=sensor.pack, name=sensor.name)
