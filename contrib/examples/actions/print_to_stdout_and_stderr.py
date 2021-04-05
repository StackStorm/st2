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

import sys
import time

from st2common.runners.base_action import Action


class PrintToStdoutAndStderrAction(Action):
    def run(self, count=100, sleep_delay=0.5):
        for i in range(0, count):
            if i % 2 == 0:
                text = "stderr"
                stream = sys.stderr
            else:
                text = "stdout"
                stream = sys.stdout

            stream.write("%s -> Line: %s\n" % (text, (i + 1)))
            stream.flush()
            time.sleep(sleep_delay)
