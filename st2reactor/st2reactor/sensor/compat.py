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

"""
Module which contains classes which are only needed for backward compatibility
purposes.
"""

import abc
import time

__all__ = [
    'StackStormV05SensorMixin',
    'StackStormV05PollingSensorMixin'
]


class StackStormV05SensorMixin(object):
    def start(self):
        self.run()

    def stop(self):
        self.cleanup()

    @abc.abstractmethod
    def get_trigger_types(self):
        """
        Return a list of available triggers exposed by this sensor.

        Note: This method has been deprecated and is only needed by sensors
        running under StackStorm v0.5.
        """
        pass


class StackStormV05PollingSensorMixin(object):
    """
    Mixin class which should be added to polling sensor classes which still
    need to work with StackStorm v0.5.

    This class implements all the methods which are still needed by StackStorm
    v0.5.
    """

    def start(self):
        while True:
            self.poll()
            time.sleep(self._poll_interval)

    def stop(self):
        self.cleanup()

    @abc.abstractmethod
    def get_trigger_types(self):
        """
        Return a list of available triggers exposed by this sensor.

        Note: This method has been deprecated and is only needed by sensors
        running under StackStorm v0.5.
        """
        pass
