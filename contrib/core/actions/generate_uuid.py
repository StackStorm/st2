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
import uuid

from st2common.runners.base_action import Action

__all__ = ["GenerateUUID"]


class GenerateUUID(Action):
    def run(self, uuid_type):
        if uuid_type == "uuid1":
            return str(uuid.uuid1())
        elif uuid_type == "uuid4":
            return str(uuid.uuid4())
        else:
            raise ValueError("Unknown uuid_type. Only uuid1 and uuid4 are supported")
