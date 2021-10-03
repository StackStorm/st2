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

from st2common.runners.base_action import Action


class IncreaseIndexAndCheckCondition(Action):
    def run(self, index, pagesize, input):
        if pagesize and pagesize != "":
            if len(input) < int(pagesize):
                return (False, "Breaking out of the loop")
        else:
            pagesize = 0

        if not index or index == "":
            index = 1

        return (True, int(index) + 1)
