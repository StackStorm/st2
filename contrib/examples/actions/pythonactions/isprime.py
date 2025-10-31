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

import math

# TODO: extend pants and pants-plugins/pack_metadata to add lib dirs extra_sys_path for pylint
from environ import get_environ  # pylint: disable=E0401
from st2common.runners.base_action import Action


class PrimeCheckerAction(Action):
    def run(self, value=0):
        self.logger.debug("PYTHONPATH: %s", get_environ("PYTHONPATH"))
        self.logger.debug("value=%s" % (value))
        if math.floor(value) != value:
            raise ValueError("%s should be an integer." % value)
        if value < 2:
            return False
        for test in range(2, int(math.floor(math.sqrt(value))) + 1):
            if value % test == 0:
                return False
        return True


if __name__ == "__main__":
    checker = PrimeCheckerAction()
    for i in range(0, 10):
        print("%s : %s" % (i, checker.run(value=1)))
