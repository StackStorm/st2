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

import abc

import six

from st2common.util import concurrency

__all__ = ["Sensor", "PollingSensor"]


@six.add_metaclass(abc.ABCMeta)
class BaseSensor(object):
    """
    Base Sensor class - not to be instantiated directly.
    """

    def __init__(self, sensor_service, config=None):
        """
        :param sensor_service: Sensor Service instance.
        :type sensor_service: :class:``st2reactor.container.sensor_wrapper.SensorService``

        :keyword config: Sensor config.
        :type config: ``dict`` or None
        """
        self._sensor_service = sensor_service  # Deprecate in the future
        self.sensor_service = sensor_service
        self._config = config or {}  # Deprecate in the future
        self.config = self._config

    @abc.abstractmethod
    def setup(self):
        """
        Run the sensor initialization / setup code (if any).
        """
        pass

    @abc.abstractmethod
    def run(self):
        """
        Run the sensor.
        """
        pass

    @abc.abstractmethod
    def cleanup(self):
        """
        Run the sensor cleanup code (if any).
        """
        pass

    @abc.abstractmethod
    def add_trigger(self, trigger):
        """
        Runs when trigger is created
        """
        pass

    @abc.abstractmethod
    def update_trigger(self, trigger):
        """
        Runs when trigger is updated
        """
        pass

    @abc.abstractmethod
    def remove_trigger(self, trigger):
        """
        Runs when trigger is deleted
        """
        pass


class Sensor(BaseSensor):
    """
    Base class to be inherited from by the passive sensors.
    """

    @abc.abstractmethod
    def run(self):
        pass


class PollingSensor(BaseSensor):
    """
    Base class to be inherited from by the active sensors.

    Active sensors periodically poll a 3rd party system for new information.
    """

    def __init__(self, sensor_service, config=None, poll_interval=5):
        super(PollingSensor, self).__init__(
            sensor_service=sensor_service, config=config
        )
        self._poll_interval = poll_interval

    @abc.abstractmethod
    def poll(self):
        """
        Poll 3rd party system for new information.
        """
        pass

    def run(self):
        while True:
            self.poll()
            concurrency.sleep(self._poll_interval)

    def get_poll_interval(self):
        """
        Retrieve current poll interval.

        :return: Current poll interval.
        :rtype: ``float``
        """
        return self._poll_interval

    def set_poll_interval(self, poll_interval):
        """
        Set the poll interval.

        :param poll_interval: Poll interval to use.
        :type poll_interval: ``float``
        """
        self._poll_interval = poll_interval
