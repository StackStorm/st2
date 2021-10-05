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

from st2reactor.sensor.base import PollingSensor


class FibonacciSensor(PollingSensor):
    def __init__(self, sensor_service, config, poll_interval=20):
        super(FibonacciSensor, self).__init__(
            sensor_service=sensor_service, config=config, poll_interval=poll_interval
        )
        self.a = None
        self.b = None
        self.count = None
        self.logger = None

    def setup(self):
        self.a = 0
        self.b = 1
        self.count = 2

        self.logger = self.sensor_service.get_logger(name=self.__class__.__name__)

    def poll(self):
        # Reset a and b if there are large enough to avoid integer overflow problems
        if self.a > 10000 or self.b > 10000:
            self.logger.debug("Reseting values to avoid integer overflow issues")

            self.a = 0
            self.b = 1
            self.count = 2

        fib = self.a + self.b
        self.logger.debug(
            "Count: %d, a: %d, b: %d, fib: %s", self.count, self.a, self.b, fib
        )

        payload = {
            "count": self.count,
            "fibonacci": fib,
            "pythonpath": os.environ.get("PYTHONPATH", None),
        }

        self.sensor_service.dispatch(trigger="examples.fibonacci", payload=payload)
        self.a = self.b
        self.b = fib
        self.count = self.count + 1

    def cleanup(self):
        pass

    def add_trigger(self, trigger):
        # This method is called when trigger is created
        pass

    def update_trigger(self, trigger):
        # This method is called when trigger is updated
        pass

    def remove_trigger(self, trigger):
        # This method is called when trigger is deleted
        pass
