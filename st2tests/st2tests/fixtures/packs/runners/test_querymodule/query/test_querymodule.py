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

from __future__ import absolute_import
from st2common.query.base import Querier
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED


class TestQuerier(Querier):
    def __init__(self, *args, **kwargs):
        super(TestQuerier, self).__init__(*args, **kwargs)

    def query(self, execution_id, query_context, last_query_time=None):
        return (LIVEACTION_STATUS_SUCCEEDED, {'called_with': {execution_id: query_context}})


def get_instance():
    return TestQuerier()
