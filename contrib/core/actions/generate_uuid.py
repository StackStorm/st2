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

import uuid
from st2actions.runners.pythonrunner import Action


class GenerateUUID(Action):
    def run(self, uuid_type):
        if uuid_type == 'uuid1':
            return str(uuid.uuid1())
        elif uuid_type == 'uuid4':
            return str(uuid.uuid4())
        else:
            raise ValueError("Unknown uuid_type. Only uuid1 and uuid4 are supported")
